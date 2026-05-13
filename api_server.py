import json
import csv
import re
import hashlib
from js import Response

# --- 유틸리티 함수 ---
def get_price_from_string(price_str):
    if isinstance(price_str, (int, float)):
        return int(price_str)
    if not isinstance(price_str, str): return None
    nums = re.findall(r'\d+', price_str.replace(',', ''))
    return int("".join(nums)) if nums else None

def hash_password(password):
    return hashlib.sha256(password.encode('utf-8')).hexdigest()

def load_csv_data(csv_text):
    lines = csv_text.strip().splitlines()
    if not lines: return []
    reader = csv.DictReader(lines)
    return list(reader)

# --- 핵심 비즈니스 로직 ---
async def calculate_best_price(item_name, user_store, user_telecom, user_telecom_tier, user_card, crawling_data, card_data, telecom_data, user_style):
    event_items = []
    if crawling_data:
        for item in crawling_data:
            name_from_db = item.get('name')
            if name_from_db and item_name.lower() in name_from_db.lower():
                price = get_price_from_string(item.get('price'))
                if price:
                    event_items.append({
                        'store': item.get('shop'),
                        'name': name_from_db,
                        'base_price': price,
                        'event': ", ".join(item.get('promotions', []))
                    })
    
    if not event_items:
        return {"message": f"아쉽게도 현재 진행 중인 '{item_name}' 행사 상품을 찾지 못했어요. 오타가 있는지 확인해 보세요!"}

    unique_names = list(set([item['name'] for item in event_items]))
    if len(unique_names) > 1:
        return {"type": "list", "message": f"'{item_name}'(으)로 검색된 상품이 여러 개 있습니다. 선택해 주세요.", "items": unique_names[:10]}

    # 1. 통신사 할인 찾기
    telecom_discount_rate = 0
    telecom_benefit_str = "없음"
    if user_store and user_telecom and user_telecom != 'none':
        for row in telecom_data:
            if user_store in row.get('partner_cvs', '') and row.get('provider', '').lower() == user_telecom.lower():
                rate = float(row.get('discount_rate', 0))
                if rate > telecom_discount_rate:
                    telecom_discount_rate = rate
                    telecom_benefit_str = f"{row['provider']} {row['tier']} ({row['details']})"

    # 2. 카드 할인 찾기
    card_discounts = []
    for row in card_data:
        benefit = str(row.get('Benefit_Details', ''))
        rate = 0
        if '%' in benefit:
            match = re.search(r'(\d+)%', benefit)
            if match: rate = int(match.group(1)) / 100
        
        target = str(row.get('Target_Brands', ''))
        if rate > 0 and (user_store in target or '주요 편의점' in target):
            card_discounts.append({'name': row['Card_Name'], 'rate': rate, 'benefit': f"{int(rate*100)}% 할인"})

    # 3. 최적 조합 계산
    item = event_items[0]
    price_after_telecom = item['base_price'] * (1 - telecom_discount_rate)
    
    best_deal = {
        'store': item['store'],
        'item_name': item['name'],
        'base_price': item['base_price'],
        'final_price': round(price_after_telecom),
        'telecom_benefit': telecom_benefit_str,
        'card_benefit': "카드 미적용"
    }

    for card in card_discounts:
        if user_card == 'none' or user_card == card['name']:
            final_with_card = price_after_telecom * (1 - card['rate'])
            if final_with_card < best_deal['final_price']:
                best_deal['final_price'] = round(final_with_card)
                best_deal['card_benefit'] = f"{card['name']} ({card['benefit']})" + (" (추천)" if user_card == 'none' else "")

    style_msg = ""
    if user_style == 'health': style_msg = "🥗 건강과 맛을 동시에! 헬시 플레저 성향에 맞춘 혜택입니다.\n\n"
    elif user_style == 'dessert': style_msg = "🍰 기분 좋은 달콤함! 디저트 러버 성향에 맞춘 혜택입니다.\n\n"
    elif user_style == 'brand': style_msg = "🏪 브랜드를 선호하시는 성향에 맞춘 혜택입니다.\n\n"
    elif user_style == 'trend': style_msg = "🔥 핫한 트렌드 상품 위주로 혜택을 정리했습니다!\n\n"

    reply = (
        f"{style_msg}'{best_deal['item_name']}' 최저가 안내입니다!\n\n"
        f"🏪 편의점: {best_deal['store']}\n"
        f"💲 최종 가격: {best_deal['final_price']:,}원 (정가: {best_deal['base_price']:,}원)\n\n"
        f"--- 적용 혜택 ---\n📱 통신사: {best_deal['telecom_benefit']}\n💳 카드: {best_deal['card_benefit']}"
    )
    return {"message": reply}

# --- Cloudflare Workers Entry Point ---
async def on_fetch(request, env):
    url = request.url
    path = "/" + "/".join(url.split("/")[3:])
    method = request.method

    headers = {
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
        "Access-Control-Allow-Headers": "*",
    }
    
    if method == "OPTIONS":
        return Response.new(None, status=204, headers=headers)

    try:
        # 데이터 로딩
        card_csv = await env.CRAWLING_KV.get("CARD_CSV") or ""
        telecom_csv = await env.CRAWLING_KV.get("TELECOM_CSV") or ""
        crawling_json = await env.CRAWLING_KV.get("CRAWLING_DATA") or "[]"
        
        card_data = load_csv_data(card_csv)
        telecom_data = load_csv_data(telecom_csv)
        crawling_data = json.loads(crawling_json)

        if path == "/search" and method == "POST":
            data = await request.json()
            item_name = data.get("item_name", "")
            user_style = data.get("user_style", "health")
            user_store = data.get("user_store")
            user_telecom = data.get("user_telecom")
            user_card = data.get("user_card", "none")

            # 1. 카드 피드백 대응 (기존 로직 유지)
            no_card_keywords = ['카드없어', '카드가없', '안써', '카드없는데', '없는데']
            if any(kw in item_name.replace(" ", "") for kw in no_card_keywords):
                 return Response.new(json.dumps({"message": "아하, 카드가 없으시군요! 괜찮습니다. 통신사 할인만으로도 충분히 저렴하게 구매하실 수 있어요!"}), headers={"Content-Type": "application/json", **headers})

            # 2. 특정 카드 문의 대응
            for row in card_data:
                if row['Card_Name'] in item_name or (len(row['Issuer']) >= 2 and row['Issuer'] in item_name):
                    store_display = user_store if user_store and user_store != 'none' else "주요 편의점"
                    reply = f"오, {row['Card_Name']} 혜택을 찾으시나요? 🔍\n\n이 카드는 {store_display}에서 **{row['Benefit_Details']}** 혜택이 있어요! 결제 시 참고해 보세요."
                    return Response.new(json.dumps({"message": reply}), headers={"Content-Type": "application/json", **headers})

            # 3. 일반 추천/검색 로직
            recommendation_keywords = ['추천', '핫한', '트렌드', '요즘', '뭐먹지', '신상']
            if any(kw in item_name for kw in recommendation_keywords):
                matched_items = []
                rec_message = "✨ 고객님 스타일을 고려한 추천 상품입니다!"
                keywords = []
                
                if user_style == 'health': keywords = ['제로', '단백질', '프로틴', '닭가슴살', '샐러드', '두부', '무설탕', '저칼로리', '그릭', '건강']
                elif user_style == 'dessert': keywords = ['초코', '케이크', '젤리', '아이스크림', '푸딩', '마카롱', '쿠키', '빵', '크림', '약과', '달콤']
                elif user_style == 'trend': keywords = ['마라', '두바이', '콜라보', '하이볼', '먹태', '요아정', '점보', '탕후루']
                else: # brand 등
                    for item in crawling_data:
                        if '1+1' in item.get('promotions', []) and (user_style != 'brand' or item.get('shop') == user_store):
                            matched_items.append(('1+1', item.get('name')))
                
                if keywords:
                    for item in crawling_data:
                        name = item.get('name', '')
                        for kw in keywords:
                            if kw in name: matched_items.append((kw, name))
                
                # 중복 제거 및 샘플링
                sample_items = []
                counts = {}
                for kw, name in matched_items:
                    limit = 20 if kw == '1+1' else 3
                    if name not in sample_items and counts.get(kw, 0) < limit:
                        sample_items.append(name)
                        counts[kw] = counts.get(kw, 0) + 1
                    if len(sample_items) >= 20: break
                
                return Response.new(json.dumps({"type": "list", "message": rec_message, "items": sample_items}), headers={"Content-Type": "application/json", **headers})

            # 최저가 검색
            result = await calculate_best_price(item_name, user_store, user_telecom, "none", user_card, crawling_data, card_data, telecom_data, user_style)
            return Response.new(json.dumps(result), headers={"Content-Type": "application/json", **headers})

        elif path == "/api/signup" and method == "POST":
            data = await request.json()
            user_id, name, phone, style = data.get("id"), data.get("name"), data.get("phone"), data.get("style")
            await env.DB.prepare("INSERT INTO users (id, name, phone, password, style) VALUES (?, ?, ?, ?, ?)").bind(user_id, name, phone, "password_placeholder", style).run()
            return Response.new(json.dumps({"message": "OK"}), headers=headers)

        elif path == "/api/login" and method == "POST":
            data = await request.json()
            user_id = data.get("id")
            result = await env.DB.prepare("SELECT id, name, style, store, carrier FROM users WHERE id = ?").bind(user_id).first()
            if result:
                return Response.new(json.dumps({"message": "OK", "user": dict(result)}), headers=headers)
            return Response.new(json.dumps({"error": "User not found"}), status=401, headers=headers)

        elif path == "/api/survey" and method == "POST":
            data = await request.json()
            user_id, store, carrier = data.get("id"), data.get("store"), data.get("carrier")
            await env.DB.prepare("UPDATE users SET store = ?, carrier = ? WHERE id = ?").bind(store, carrier, user_id).run()
            return Response.new(json.dumps({"message": "OK"}), headers=headers)

        return Response.new("Not Found", status=404, headers=headers)

    except Exception as e:
        return Response.new(json.dumps({"error": str(e)}), status=500, headers=headers)