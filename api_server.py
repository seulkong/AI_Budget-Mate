from flask import Flask, request, jsonify
import pandas as pd
import json
from flask_cors import CORS
import os
import sys
import re
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

# --- 전역 변수 선언 ---
crawling_data = []
card_df = pd.DataFrame()
telecom_df = pd.DataFrame()
# --------------------

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

def calculate_best_price(item_name, user_store, user_telecom):
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
        return {"message": f"'{item_name}'에 대한 편의점 행사 정보를 찾을 수 없습니다."}

    # 2. 사용자의 통신사 할인율 찾기
    telecom_discount_rate = 0
    telecom_benefit_str = "없음"
    if not telecom_df.empty and user_store and user_telecom:
        telecom_info = telecom_df[
            telecom_df['partner_cvs'].str.contains(user_store, na=False) &
            (telecom_df['provider'] == user_telecom)
        ]
        if not telecom_info.empty:
            best_telecom = telecom_info.sort_values(by='discount_rate', ascending=False).iloc[0]
            telecom_discount_rate = best_telecom['discount_rate']
            telecom_benefit_str = f"{best_telecom['provider']} {best_telecom['tier']} ({best_telecom['details']})"

    # 3. 적용 가능한 모든 카드 할인율 찾기
    card_discounts = []
    if not card_df.empty:
        card_info = card_df[card_df['merchant_category'].str.contains('All CVS', na=False)]
        for _, row in card_info.iterrows():
            card_discounts.append({
                'name': row['card_name'],
                'rate': row['discount_rate'],
                'benefit': f"{row['discount_rate']*100}% 할인 (전월 실적: {row['min_performance']}원)"
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
            final_price_with_card = price_after_telecom * (1 - card['rate'])
            if final_price_with_card < best_deal['final_price']:
                best_deal['final_price'] = round(final_price_with_card)
                best_deal['card_benefit'] = f"{card['name']} ({card['benefit']})"

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

        reply = (
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
        card_info = card_df[
            card_df['merchant_category'].str.contains('All CVS', na=False) |
            card_df['merchant_category'].isin(list(stores_to_check_cards))
        ]
        for _, row in card_info.iterrows():
            results.append({
                "type": "카드 할인",
                "card_name": row['card_name'],
                "benefit": f"{row['discount_rate']*100}% 할인 (전월 실적: {row['min_performance']}원)"
            })

    # --- 최종 결과 처리 로직 수정 ---
    if not results:
        # 최종적으로 results 리스트가 비어있으면, 명확한 메시지를 반환합니다.
        if user_store:
            return {"message": f"'{item_name}'에 대한 행사 정보나 관련 혜택을 찾을 수 없습니다."}
        else:
            return {"message": f"'{item_name}'에 대한 할인 정보를 찾을 수 없습니다. 먼저 설문조사를 통해 선호 편의점을 알려주세요."}
            
    return results

@app.route('/search', methods=['POST'])
def search():
    """챗봇 요청을 받아 처리하는 API 엔드포인트"""
    try:
        data = request.json
        item_name = data.get('item_name')
        user_info = data.get('user_info', {})
        user_store = user_info.get('store')
        user_telecom = user_info.get('carrier')

        if not item_name:
            return jsonify({"error": "상품명을 입력해주세요."}), 400
        
        result = calculate_best_price(item_name, user_store, user_telecom)
        return jsonify(result)
    except Exception as e:
        print(f"An error occurred during search: {e}")
        return jsonify({"error": "서버 내부 오류가 발생했습니다."}), 500

# --- if __name__ == '__main__': 블록은 로컬 테스트용으로만 사용 ---
if __name__ == '__main__':
    # 로컬에서 직접 실행할 때만 사용됩니다.
    # Render(Gunicorn) 환경에서는 이 부분이 실행되지 않습니다.
    print("로컬 개발 서버를 시작합니다...")
    app.run(host='0.0.0.0', port=5001, debug=True)