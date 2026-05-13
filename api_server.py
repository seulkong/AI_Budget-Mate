from flask import Flask, request, jsonify
import pandas as pd
import json
from flask_cors import CORS
import os
import sys
import re
import requests
import sqlite3
import hashlib
# pyrefly: ignore [missing-import]
from apscheduler.schedulers.background import BackgroundScheduler

# --- 경로 수정 ---
# 데이터 파일들이 api_server.py와 동일한 폴더에 있다고 가정합니다.
# 'AI_Budget-Mate' 폴더 구조를 제거하고 경로를 단순화합니다.
sys.path.append(os.path.dirname(__file__))
try:
    from crawling import crawl_convenience_store
except ImportError:
    # Render 환경에서는 crawling 모듈이 없을 수 있으므로 예외 처리
    def crawl_convenience_store(store, max_pages):
        print(f"Warning: 'crawling' module not found. Cannot crawl {store}.")
        return []

CRAWLING_RESULT_PATH = os.path.join(os.path.dirname(__file__), 'crawling_result.json')
CARD_DATA_PATH = os.path.join(os.path.dirname(__file__), 'Card.csv')
TELECOM_DATA_PATH = os.path.join(os.path.dirname(__file__), 'Telecom.csv')
# -------------------------------------------------

app = Flask(__name__)
CORS(app)

KAKAO_KEY = "28927acb4f3229bf2bddf11261cc6ff3"
DB_PATH = os.path.join(os.path.dirname(__file__), 'users.db')

# --- 전역 변수 선언 ---
crawling_data = []
card_df = pd.DataFrame()
telecom_df = pd.DataFrame()
# --------------------

def init_db():
    """SQLite 데이터베이스 초기화 및 테이블 생성"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            phone TEXT NOT NULL,
            password TEXT NOT NULL,
            store TEXT,
            carrier TEXT
        )
    ''')
    conn.commit()
    conn.close()
    print("✅ 데이터베이스 초기화 완료")

def hash_password(password):
    """비밀번호 해싱 (간단한 SHA-256)"""
    return hashlib.sha256(password.encode('utf-8')).hexdigest()

def load_data():
    """모든 데이터 소스를 로드하여 전역 변수를 업데이트하는 함수"""
    global crawling_data, card_df, telecom_df
    print("데이터 로드를 시작합니다...")
    try:
        with open(CRAWLING_RESULT_PATH, 'r', encoding='utf-8') as f:
            content = f.read()
            crawling_data = json.loads(content) if content else []
        print(f"✅ 크롤링 데이터 로드 완료 ({len(crawling_data)}개 항목)")
    except (FileNotFoundError, json.JSONDecodeError) as e:
        crawling_data = []
        print(f"⚠️ 크롤링 데이터 파일({CRAWLING_RESULT_PATH})을 찾을 수 없거나 파싱 오류가 발생했습니다: {e}")

    try:
        card_df = pd.read_csv(CARD_DATA_PATH)
        print(f"✅ 카드 데이터 로드 완료 ({len(card_df)}개 행)")
    except FileNotFoundError as e:
        card_df = pd.DataFrame()
        print(f"⚠️ 카드 데이터 파일({CARD_DATA_PATH})을 찾을 수 없습니다: {e}")

    try:
        telecom_df = pd.read_csv(TELECOM_DATA_PATH)
        print(f"✅ 통신사 데이터 로드 완료 ({len(telecom_df)}개 행)")
    except FileNotFoundError as e:
        telecom_df = pd.DataFrame()
        print(f"⚠️ 통신사 데이터 파일({TELECOM_DATA_PATH})을 찾을 수 없습니다: {e}")

def run_crawling_and_save():
    """주기적으로 크롤링을 실행하고 결과를 JSON 파일에 저장하는 함수"""
    print("===== 자동 크롤링 시작 =====")
    try:
        all_data = []
        gs25_data = crawl_convenience_store("GS25", max_pages=135)
        all_data.extend(gs25_data)
        cu_data = crawl_convenience_store("CU", max_pages=123)
        all_data.extend(cu_data)

        # Render의 임시 파일 시스템에 저장
        with open(CRAWLING_RESULT_PATH, 'w', encoding='utf-8') as f:
            json.dump(all_data, f, ensure_ascii=False, indent=4)
        
        print(f"✅ 자동 크롤링 완료! 총 {len(all_data)}개의 데이터가 저장되었습니다.")
        # 크롤링 후 즉시 메모리에 데이터를 다시 로드
        load_data()
    except Exception as e:
        print(f"❌ 자동 크롤링 중 오류 발생: {e}")

# --- 서버 시작 시 데이터 로드 및 스케줄러 설정 ---
# Gunicorn이 앱을 임포트할 때 이 코드가 실행됩니다.
init_db() # 데이터베이스 테이블 생성
load_data() # 서버 시작 시 데이터 즉시 로드

scheduler = BackgroundScheduler(daemon=True)
scheduler.add_job(run_crawling_and_save, 'interval', hours=6)
scheduler.start()
print("Flask 서버 설정 완료. 스케줄러가 시작되었습니다.")
# -------------------------------------------------

def get_price_from_string(price_str):
    """'1,700원' 또는 숫자 1700 같은 값에서 숫자 1700을 추출합니다."""
    if isinstance(price_str, (int, float)):
        return int(price_str)
    if not isinstance(price_str, str): return None
    nums = re.findall(r'\d+', price_str.replace(',', ''))
    return int("".join(nums)) if nums else None

def calculate_best_price(item_name, user_store, user_telecom, user_telecom_tier='none', user_card='none', user_style='health'):
    """모든 할인을 적용하여 최저가를 계산하는 핵심 함수"""
    
    # 1. 행사 상품 정보 찾기 (대소문자 구분 없이)
    event_items = []
    if crawling_data:
        for item in crawling_data:
            item_name_from_db = item.get('name')
            if item and item_name_from_db and isinstance(item_name_from_db, str):
                if item_name.lower() in item_name_from_db.lower():
                    price = get_price_from_string(item.get('price'))
                    if price:
                        event_items.append({
                            'store': item.get('shop'),
                            'name': item_name_from_db,
                            'base_price': price,
                            'event': ", ".join(item.get('promotions', []))
                        })
    
    if not event_items:
        return {
            "message": f"아쉽게도 현재 진행 중인 '{item_name}' 행사 상품을 찾지 못했어요. 오타가 있는지 확인해 보시거나, '우유', '라면' 처럼 조금 더 짧은 단어로 다시 검색해 보시겠어요?"
        }

    unique_item_names = list(set([item['name'] for item in event_items]))
    
    # 여러 상품이 매칭되는 경우 (단, 정확히 일치하는 이름이 하나만 있다면 그걸로 간주)
    exact_match = [name for name in unique_item_names if name.lower() == item_name.lower()]
    if exact_match:
        unique_item_names = exact_match
        event_items = [item for item in event_items if item['name'].lower() == item_name.lower()]
        
    if len(unique_item_names) > 1:
        # 상품 리스트 반환 (최대 10개로 제한하여 너무 길어지지 않게 함)
        return {
            "type": "list", 
            "message": f"'{item_name}'(으)로 검색된 상품이 여러 개 있습니다. 정확히 어떤 상품을 찾으시나요? 아래에서 선택해 주세요.", 
            "items": unique_item_names[:10]
        }

    # 2. 사용자의 통신사 할인율 찾기
    telecom_discount_rate = 0
    telecom_benefit_str = "없음"
    if not telecom_df.empty and user_store and user_telecom and user_telecom != 'none':
        # 통신사 이름 필터링 (대소문자 무시)
        telecom_info = telecom_df[
            telecom_df['partner_cvs'].str.contains(user_store, na=False) &
            (telecom_df['provider'].str.lower() == user_telecom.lower())
        ]
        
        if not telecom_info.empty:
            # 등급 필터링
            if user_telecom_tier == 'high':
                tier_info = telecom_info[telecom_info['tier'].str.contains('VIP|Gold', case=False, na=False)]
            elif user_telecom_tier == 'low':
                tier_info = telecom_info[telecom_info['tier'].str.contains('Silver|General', case=False, na=False)]
            else:
                tier_info = telecom_info # 등급 정보가 없으면 전체에서 찾음
                
            if tier_info.empty:
                tier_info = telecom_info # 매칭되는 등급이 없으면 전체에서 기본값 찾기
                
            best_telecom = tier_info.sort_values(by='discount_rate', ascending=False).iloc[0]
            telecom_discount_rate = best_telecom['discount_rate']
            telecom_benefit_str = f"{best_telecom['provider']} {best_telecom['tier']} ({best_telecom['details']})"

    # 3. 적용 가능한 모든 카드 할인율 찾기
    card_discounts = []
    if not card_df.empty:
        for _, row in card_df.iterrows():
            card_name = row.get('Card_Name', '')
            benefit_details = str(row.get('Benefit_Details', ''))
            target_brands = str(row.get('Target_Brands', ''))
            
            # 할인율 파싱 (예: "10% 청구 할인" -> 0.1)
            rate = 0
            if '%' in benefit_details:
                try:
                    num_str = re.search(r'(\d+)%', benefit_details).group(1)
                    rate = int(num_str) / 100
                except:
                    pass

            if rate > 0 and ((user_store and user_store in target_brands) or '주요 편의점' in target_brands):
                card_discounts.append({
                    'name': card_name,
                    'rate': rate,
                    'benefit': f"{int(rate*100)}% 할인 ({row.get('Minimum_Spending', '조건없음')})"
                })

    # 4. 모든 조합을 계산하여 최저가 찾기
    best_deal = None

    for item in event_items:
        current_telecom_rate = telecom_discount_rate if item['store'] == user_store else 0
        price_after_telecom = item['base_price'] * (1 - current_telecom_rate)
        final_price = price_after_telecom
        deal_info = {
            'store': item['store'],
            'item_name': item['name'],
            'base_price': item['base_price'],
            'final_price': round(final_price),
            'telecom_benefit': telecom_benefit_str if current_telecom_rate > 0 else "없음",
            'card_benefit': "카드 미적용"
        }
        if best_deal is None or deal_info['final_price'] < best_deal['final_price']:
            best_deal = deal_info

        for card in card_discounts:
            # 설문에서 카드를 선택하지 않았거나(none), 선택한 카드와 일치할 때만 적용
            if user_card == 'none' or user_card == card['name']:
                final_price_with_card = price_after_telecom * (1 - card['rate'])
                if final_price_with_card < best_deal['final_price']:
                    best_deal['final_price'] = round(final_price_with_card)
                    best_deal['card_benefit'] = f"{card['name']} ({card['benefit']})" + (" (추천)" if user_card == 'none' else "")

    # 5. 최종 결과 메시지 생성
    if best_deal:
        # --- 편의점별 행사 내용 요약 로직 추가 ---
        promotions_summary = {
            "GS25": "행사 없음",
            "CU": "행사 없음"
        }
        for item in event_items:
            store = item.get('store')
            event = item.get('event')
            if store in promotions_summary and event:
                promotions_summary[store] = event
        
        gs25_promo_str = promotions_summary["GS25"]
        cu_promo_str = promotions_summary["CU"]
        # -----------------------------------------

        style_msg = ""
        if user_style == 'health':
            style_msg = "건강과 맛을 동시에! 칼로리와 영양을 챙기시는 성향에 맞춰 혜택을 정리했습니다!\n\n"
        elif user_style == 'dessert':
            style_msg = "기분 좋은 달콤함! 디저트 러버 성향에 맞춰 맛있는 혜택을 정리했습니다!\n\n"
        elif user_style == 'brand':
            style_msg = "브랜드를 선호하시는 성향을 고려해 맞춤형으로 혜택을 정리했습니다!\n\n"
        elif user_style == 'trend':
            style_msg = "트렌디한 감각에 맞춰 현재 제일 잘 나가는 핫한 아이템 정보로 혜택을 찾아봤어요!\n\n"
        else:
            style_msg = ""

        reply = (
            f"{style_msg}"
            f"'{best_deal['item_name']}' 최저가 구매 방법입니다!\n\n"
            f"🏪 편의점: {best_deal['store']}\n"
            f"💲 최종 가격: 약 {best_deal['final_price']:,}원 (정가: {best_deal['base_price']:,}원)\n\n"
            f"--- 적용된 혜택 ---\n"
            f"📱 통신사: {best_deal['telecom_benefit']}\n"
            f"💳 카  드: {best_deal['card_benefit']}\n\n"
            f"---편의점 별 행사 내용--\n"
            f"GS25: {gs25_promo_str}\n"
            f"CU: {cu_promo_str}"
        )
        return {"message": reply}
    
    return {"message": "오류: 최적의 할인 조합을 계산하는 데 실패했습니다."}


def find_best_deal(item_name, user_store, user_telecom):
    """편의점 행사, 통신사, 카드 혜택을 종합하여 최적의 조합을 찾는 함수"""
    results = []
    found_stores = set()

    # 1. 크롤링 데이터에서 '편의점 행사' 정보 검색
    if crawling_data:
        for item in crawling_data:
            if item and item.get('name') and item_name in item['name']:
                results.append({
                    "type": "편의점 행사",
                    "store": item.get('shop', 'N/A'),
                    "item_name": item['name'],
                    "price": f"{item.get('price', '가격정보없음')}원",
                    "event": ", ".join(item.get('promotions', []))
                })
                if item.get('shop'):
                    found_stores.add(item['shop'])
    
    # 2. 사용자의 '통신사 할인' 정보 검색
    if not telecom_df.empty and user_store and user_telecom:
        telecom_info = telecom_df[
            telecom_df['partner_cvs'].str.contains(user_store, na=False) &
            (telecom_df['provider'] == user_telecom)
        ]
        for _, row in telecom_info.iterrows():
            results.append({
                "type": "통신사 할인",
                "store": user_store,
                "telecom": row['provider'],
                "benefit": f"{row['tier']} 등급, {row['details']}"
            })

    # 3. 관련된 '카드 할인' 정보 검색
    stores_to_check_cards = found_stores
    if not stores_to_check_cards and user_store:
        stores_to_check_cards = {user_store}

    if not card_df.empty and stores_to_check_cards:
        for store in stores_to_check_cards:
            card_info = card_df[card_df['Target_Brands'].str.contains(store, na=False) | card_df['Target_Brands'].str.contains('주요 편의점', na=False)]
            for _, row in card_info.iterrows():
                results.append({
                    "type": "카드 할인",
                    "card_name": row.get('Card_Name', ''),
                    "benefit": str(row.get('Benefit_Details', '')) + f" ({row.get('Minimum_Spending', '')})"
                })

    # --- 최종 결과 처리 로직 수정 ---
    if not results:
        # 최종적으로 results 리스트가 비어있으면, 명확한 메시지를 반환합니다.
        if user_store:
            return {"message": f"'{item_name}'에 대한 행사 정보나 관련 혜택을 찾을 수 없습니다."}
        else:
            return {"message": f"'{item_name}'에 대한 할인 정보를 찾을 수 없습니다. 먼저 설문조사를 통해 선호 편의점을 알려주세요."}
            
    return results

@app.route('/api/signup', methods=['POST'])
def signup():
    """회원가입 API"""
    try:
        data = request.json
        user_id = data.get('id')
        name = data.get('name')
        phone = data.get('phone')
        password = data.get('password')

        if not all([user_id, name, phone, password]):
            return jsonify({"error": "모든 필드를 입력해주세요."}), 400

        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # ID 중복 확인
        cursor.execute("SELECT id FROM users WHERE id = ?", (user_id,))
        if cursor.fetchone():
            conn.close()
            return jsonify({"error": "이미 존재하는 ID입니다."}), 409

        # 유저 추가
        hashed_pw = hash_password(password)
        cursor.execute(
            "INSERT INTO users (id, name, phone, password) VALUES (?, ?, ?, ?)",
            (user_id, name, phone, hashed_pw)
        )
        conn.commit()
        conn.close()
        return jsonify({"message": "회원가입이 완료되었습니다."}), 201

    except Exception as e:
        print(f"Signup error: {e}")
        return jsonify({"error": "서버 오류가 발생했습니다."}), 500

@app.route('/api/login', methods=['POST'])
def login():
    """로그인 API"""
    try:
        data = request.json
        user_id = data.get('id')
        password = data.get('password')

        if not user_id or not password:
            return jsonify({"error": "ID와 비밀번호를 모두 입력해주세요."}), 400

        hashed_pw = hash_password(password)
        
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT id, name FROM users WHERE id = ? AND password = ?", (user_id, hashed_pw))
        user = cursor.fetchone()
        conn.close()

        if user:
            return jsonify({"message": "로그인 성공", "user": {"id": user[0], "name": user[1]}}), 200
        else:
            return jsonify({"error": "ID 또는 비밀번호가 올바르지 않습니다."}), 401

    except Exception as e:
        print(f"Login error: {e}")
        return jsonify({"error": "서버 오류가 발생했습니다."}), 500

@app.route('/api/survey', methods=['POST'])
def survey():
    """설문조사 결과 저장 API"""
    try:
        data = request.json
        user_id = data.get('id')
        store = data.get('store')
        carrier = data.get('carrier')

        if not all([user_id, store, carrier]):
            return jsonify({"error": "필수 정보가 누락되었습니다."}), 400

        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("UPDATE users SET store = ?, carrier = ? WHERE id = ?", (store, carrier, user_id))
        
        if cursor.rowcount == 0:
            conn.close()
            return jsonify({"error": "존재하지 않는 사용자입니다."}), 404
            
        conn.commit()
        conn.close()
        return jsonify({"message": "설문조사가 저장되었습니다."}), 200

    except Exception as e:
        print(f"Survey error: {e}")
        return jsonify({"error": "서버 오류가 발생했습니다."}), 500

@app.route('/search', methods=['POST'])
def search():
    """챗봇 요청을 받아 처리하는 API 엔드포인트"""
    try:
        data = request.json
        item_name = data.get('item_name')
        
        # 클라이언트에서 직접 전달된 설문 데이터
        user_style = data.get('user_style', 'health')
        user_store = data.get('user_store')
        user_telecom = data.get('user_telecom')
        user_telecom_tier = data.get('user_telecom_tier', 'none')
        user_card = data.get('user_card', 'none')

        if not item_name:
            return jsonify({"error": "상품명을 입력해주세요."}), 400

        # --- [카드 관련 문의 처리] ---
        # 1. 카드가 없다는 피드백 대응
        no_card_keywords = ['카드없어', '카드가없', '안써', '카드없는데', '없는데', '카드아예없어']
        clean_item_name = item_name.replace(" ", "")
        if any(kw in clean_item_name for kw in no_card_keywords):
             return jsonify({"message": "아하, 해당 카드를 가지고 있지 않으시군요! 💳 괜찮습니다. 카드가 없어도 통신사 할인만으로 충분히 혜택을 받으실 수 있어요. 혹은 현재 가지고 계신 다른 카드 이름을 말씀해 주시면 혜택이 있는지 바로 확인해 드릴게요!"})
             
        # 2. 특정 카드 언급 확인 (데이터베이스 연동)
        if not card_df.empty:
            found_card = None
            for _, row in card_df.iterrows():
                c_name = str(row['Card_Name'])
                c_issuer = str(row['Issuer'])
                # 메시지에 카드 이름이나 카드사(2글자 이상)가 포함되어 있는지 확인
                if (c_name in item_name) or (len(c_issuer) >= 2 and c_issuer in item_name):
                    found_card = row
                    break
            
            if found_card is not None:
                store_display = user_store if user_store and user_store != 'none' else "주요 편의점"
                reply = (
                    f"오, {found_card['Card_Name']}을(를) 가지고 계시군요! 잠시만요... 🔍\n\n"
                    f"확인 결과, 이 카드는 {store_display}에서 **{found_card['Benefit_Details']}** 혜택이 있네요! "
                    f"({found_card['Minimum_Spending']} 조건)\n\n"
                    f"이 카드로 결제하시면 더 저렴하게 구매 가능합니다. 다른 궁금한 점이 있으신가요?"
                )
                return jsonify({"message": reply})
        # ----------------------------
        # --- [추천 시스템 분기] ---
        recommendation_keywords = ['추천', '핫한', '트렌드', '요즘', '뭐먹지', '신상']
        is_recommendation = any(kw in item_name for kw in recommendation_keywords)
        
        if is_recommendation:
            if not crawling_data:
                return jsonify({"message": "현재 행사 데이터를 불러올 수 없습니다."})
                
            matched_items = []
            rec_message = ""
            keywords = []
            
            if user_style == 'health':
                keywords = ['제로', '단백질', '프로틴', '닭가슴살', '샐러드', '두부', '무설탕', '저칼로리', '그릭', '건강']
                rec_message = "🥗 헬시 플레저를 위한 건강한 간식들을 모아봤어요! 관심 있는 상품을 선택해 보세요."
            elif user_style == 'dessert':
                keywords = ['초코', '케이크', '젤리', '아이스크림', '푸딩', '마카롱', '쿠키', '빵', '크림', '약과', '달콤']
                rec_message = "🍰 당 충전이 필요하신가요? 보기만 해도 달콤한 디저트들을 모아봤어요!"
            elif user_style == 'trend':
                keywords = ['마라', '두바이', '콜라보', '하이볼', '먹태', '요아정', '점보', '탕후루']
                rec_message = "🔥 요즘 SNS에서 제일 핫한 트렌드 상품들이에요! 관심 있는 상품을 선택해 보세요."
            else: # brand 등
                # 브랜드 선호는 선택한 편의점의 1+1 위주로 추천
                for item in crawling_data:
                    promos = item.get('promotions', [])
                    name = item.get('name')
                    store = item.get('shop')
                    if name and isinstance(name, str):
                        # 브랜드 선호면 선호 편의점만 필터링
                        if user_style == 'brand' and user_store and user_store != 'none' and store != user_store:
                            continue
                        if '1+1' in promos:
                            matched_items.append(('1+1', name))
                rec_message = f"🏪 선호하시는 {user_store} 편의점의 대박 1+1 행사 상품들을 모아봤어요!"

            # 키워드 기반 매칭 (health, dessert, trend)
            if keywords:
                for item in crawling_data:
                    name = item.get('name')
                    if name and isinstance(name, str):
                        for kw in keywords:
                            if kw in name:
                                matched_items.append((kw, name))
            
            if matched_items:
                import random
                random.shuffle(matched_items)
                
                # 다양한 키워드가 나오도록 제한
                sample_items = []
                keyword_counts = {}
                
                for kw, name in matched_items:
                    if name not in sample_items:
                        # 1+1 상품은 제한을 크게(20개) 풀고, 다른 키워드는 다양성을 위해 3개로 조정
                        limit = 20 if kw == '1+1' else 3
                        if keyword_counts.get(kw, 0) < limit:
                            sample_items.append(name)
                            keyword_counts[kw] = keyword_counts.get(kw, 0) + 1
                    
                    if len(sample_items) >= 20:
                        break
                        
                return jsonify({
                    "type": "list",
                    "message": rec_message,
                    "items": sample_items
                })
            else:
                return jsonify({"message": "현재 해당 성향에 맞는 추천 상품 정보가 없네요. 일반 상품을 검색해 보세요!"})
        # ------------------------
        
        result = calculate_best_price(item_name, user_store, user_telecom, user_telecom_tier, user_card, user_style)
        return jsonify(result)
    except Exception as e:
        print(f"An error occurred during search: {e}")
        return jsonify({"error": "서버 내부 오류가 발생했습니다."}), 500

@app.route('/nearby_stores', methods=['GET'])
def nearby_stores():
    """사용자의 위도/경도를 받아 근처 편의점(GS25, CU) 목록을 반환하는 엔드포인트"""
    try:
        lat = request.args.get('lat')
        lon = request.args.get('lon')
        
        if not lat or not lon:
            return jsonify({"error": "위도(lat)와 경도(lon)가 필요합니다."}), 400
            
        url = "https://dapi.kakao.com/v2/local/search/category.json"
        headers = {"Authorization": f"KakaoAK {KAKAO_KEY}"}
        params = {
            "category_group_code": "CS2", 
            "x": lon, 
            "y": lat, 
            "radius": 1000,
            "sort": "distance"
        }
        
        res = requests.get(url, headers=headers, params=params)
        
        if res.status_code != 200:
            return jsonify({"error": "카카오 API 요청에 실패했습니다."}), res.status_code
            
        documents = res.json().get('documents', [])
        
        # GS25와 CU만 필터링
        filtered_docs = [
            doc for doc in documents 
            if "GS25" in doc.get("place_name", "").upper() or "CU" in doc.get("place_name", "").upper()
        ]
        
        return jsonify(filtered_docs)
    except Exception as e:
        print(f"An error occurred during nearby_stores: {e}")
        return jsonify({"error": "서버 내부 오류가 발생했습니다."}), 500

# --- if __name__ == '__main__': 블록은 로컬 테스트용으로만 사용 ---
if __name__ == '__main__':
    # 로컬에서 직접 실행할 때만 사용됩니다.
    # Render(Gunicorn) 환경에서는 이 부분이 실행되지 않습니다.
    print("로컬 개발 서버를 시작합니다...")
    app.run(host='0.0.0.0', port=5001, debug=True)