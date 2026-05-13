import json
from js import Response, Headers, Object

async def on_fetch(request, env):
    headers = Headers.new()
    headers.set("Access-Control-Allow-Origin", "*")
    headers.set("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
    headers.set("Access-Control-Allow-Headers", "*")
    headers.set("Content-Type", "application/json")
    
    method = request.method
    url = request.url
    path = "/" + "/".join(url.split("/")[3:])
    if "?" in path:
        path = path.split("?")[0]

    if method == "OPTIONS":
        return Response.new("", status=204, headers=headers)

    try:
        if path == "/search" and method == "POST":
            js_data = await request.json()
            data = js_data.to_py()
            
            item_name = data.get("item_name", "").strip()
            user_style = data.get("user_style", "health")
            user_store = data.get("user_store", "GS25")
            user_telecom = data.get("user_telecom", "none")
            user_telecom_tier = data.get("user_telecom_tier", "low")
            user_card = data.get("user_card", "none")

            # 1. 카드 피드백 대응
            no_card_keywords = ['카드없어', '카드가없', '안써', '카드없는데', '없는데']
            if any(kw in item_name.replace(" ", "") for kw in no_card_keywords):
                 return Response.new(json.dumps({"message": "아하, 카드가 없으시군요! 괜찮습니다. 통신사 할인만으로도 충분히 저렴하게 구매하실 수 있어요!"}), headers=headers)

            # 2. KV 데이터 로드
            crawling_raw = await env.CRAWLING_KV.get("crawling_result.json")
            crawling_data = json.loads(crawling_raw) if crawling_raw else []

            # 3. 특정 카드 문의 대응
            try:
                card_csv_raw = await env.CRAWLING_KV.get("Card.csv")
                if card_csv_raw:
                    import csv, io
                    f = io.StringIO(card_csv_raw)
                    card_reader = list(csv.DictReader(f))
                    for row in card_reader:
                        if row['Card_Name'] in item_name or (len(row['Issuer']) >= 2 and row['Issuer'] in item_name):
                            return Response.new(json.dumps({"message": f"오! {row['Card_Name']} 카드군요. 이 카드는 {row['Benefit']} 혜택이 있어요. {row['Issuer']} 제휴 할인이랑 같이 쓰면 더 좋아요!"}), headers=headers)
            except: pass

            # 4. 상품 추천 및 리스트 검색 로직
            # 검색어가 여러 상품에 걸리거나 '추천' 요청인 경우 리스트로 응답
            recommend_keywords = ['추천', '뭐가', '뭐있어', '보여줘', '핫한', '골라줘']
            is_recommend = any(kw in item_name for kw in recommend_keywords)
            
            search_results = [i for i in crawling_data if item_name in i.get('name', '')]
            
            # 리스트로 보여줘야 하는 경우 (검색 결과가 여러 개이거나 추천 요청인 경우)
            if is_recommend or (len(search_results) > 1 and item_name not in [i['name'] for i in search_results]):
                options = []
                if is_recommend:
                    style_keywords = {
                        'health': ['제로', '단백질', '닭가슴살', '건강', '샐러드', '무설탕'],
                        'dessert': ['초코', '마카롱', '케이크', '디저트', '푸딩', '달콤'],
                        'trend': ['마라', '요아정', '두바이', '신상', '대란', '인기']
                    }
                    kws = style_keywords.get(user_style, [])
                    # 1+1 및 키워드 매칭 상품 추출
                    for item in crawling_data:
                        if ('1+1' in item.get('promotions', [])) or any(k in item.get('name') for k in kws):
                             if user_style != 'brand' or item.get('shop') == user_store:
                                 options.append(item.get('name'))
                else:
                    options = [i['name'] for i in search_results]

                # 중복 제거 및 20개 제한
                options = list(dict.fromkeys(options))[:20]
                
                if options:
                    msg = "원하시는 상품을 선택해 주세요! 최적의 할인을 찾아드릴게요."
                    if is_recommend:
                        msg = f"{user_style.upper()} 스타일에 딱 맞는 추천 리스트입니다! 하나를 골라보세요."
                    return Response.new(json.dumps({
                        "type": "list",
                        "message": msg,
                        "options": options
                    }), headers=headers)

            # 5. 단일 상품 최적가 계산 (이전 로직 유지)
            if not search_results:
                return Response.new(json.dumps({"message": f"아쉽게도 '{item_name}' 상품은 현재 행사 중이 아니에요. 다른 상품을 검색해 보시겠어요?"}), headers=headers)
            
            best_item = search_results[0]
            # 정확히 일치하는 상품이 있으면 그것을 우선 사용
            exact_match = [i for i in search_results if i['name'] == item_name]
            if exact_match:
                best_item = exact_match[0]

            base_price = int(str(best_item.get('price', '0')).replace(',', '').replace('원', ''))
            shop = best_item.get('shop', 'GS25')
            
            final_price = base_price
            discount_details = []
            
            promo = best_item.get('promotions', [])
            if '1+1' in promo:
                final_price = base_price / 2
                discount_details.append(f"• [행사] 1+1 적용 (개당 -{int(base_price/2):,}원)")
            elif '2+1' in promo:
                final_price = (base_price * 2) / 3
                discount_details.append(f"• [행사] 2+1 적용 (3개 구매 시 개당 -{int(base_price/3):,}원)")
            
            try:
                telecom_raw = await env.CRAWLING_KV.get("Telecom.csv")
                if telecom_raw and user_telecom != 'none' and user_telecom != '':
                    import csv, io
                    f = io.StringIO(telecom_raw)
                    tel_reader = list(csv.DictReader(f))
                    for row in tel_reader:
                        if row['Telecom'] == user_telecom and row['Shop'] == shop:
                            discount_per_unit = 0
                            if user_telecom_tier == 'high':
                                discount_per_unit = int(row['Discount_VIP'].replace('원', '').replace(',', '')) if '원' in row['Discount_VIP'] else 0
                            else:
                                discount_per_unit = int(row['Discount_Normal'].replace('원', '').replace(',', '')) if '원' in row['Discount_Normal'] else 0
                            
                            if discount_per_unit > 0:
                                final_price -= discount_per_unit
                                discount_details.append(f"• [통신사] {user_telecom} 멤버십 할인 (-{discount_per_unit:,}원)")
                            break
            except: pass

            if user_card != 'none' and user_card != '':
                card_discount = 0
                if ('삼성' in user_card and shop == 'GS25') or ('신한' in user_card and shop == 'CU') or ('국민' in user_card and shop == 'GS25') or ('노리' in user_card):
                    card_discount = int(final_price * 0.1)
                    final_price -= card_discount
                    discount_details.append(f"• [카드] {user_card} 제휴 추가 10% 할인 (-{card_discount:,}원)")

            msg = f"🔍 '{best_item['name']}' ({shop}) 최적의 구매 조합을 찾았습니다!\n\n"
            msg += f"기본 가격: {base_price:,}원\n"
            if discount_details:
                msg += "\n[적용된 할인 혜택]\n" + "\n".join(discount_details) + "\n"
            msg += f"\n✨ 최종 혜택가: {int(final_price):,}원"
            
            if '1+1' in promo:
                msg += f"\n(1+1 행사로 총 {base_price:,}원에 2개를 득템하세요!)"
            elif '2+1' in promo:
                msg += f"\n(2+1 행사로 총 {base_price*2:,}원에 3개를 득템하세요!)"

            return Response.new(json.dumps({"message": msg}), headers=headers)

        elif path == "/api/signup" and method == "POST":
            js_data = await request.json()
            data = js_data.to_py()
            user_id, name, style = data.get("id"), data.get("name"), data.get("style")
            await env.DB.prepare("INSERT INTO users (id, name, style) VALUES (?, ?, ?)").bind(user_id, name, style).run()
            return Response.new(json.dumps({"message": "OK"}), headers=headers)

        elif path == "/api/login" and method == "POST":
            js_data = await request.json()
            data = js_data.to_py()
            user_id = data.get("id")
            result = await env.DB.prepare("SELECT id, name, style, store, carrier FROM users WHERE id = ?").bind(user_id).first()
            if result:
                user_dict = result.to_py() if hasattr(result, "to_py") else dict(result)
                return Response.new(json.dumps({"message": "OK", "user": user_dict}), headers=headers)
            return Response.new(json.dumps({"error": "User not found"}), status=401, headers=headers)

        elif path == "/api/survey" and method == "POST":
            js_data = await request.json()
            data = js_data.to_py()
            user_id, store, carrier = data.get("id"), data.get("store"), data.get("carrier")
            await env.DB.prepare("UPDATE users SET store = ?, carrier = ? WHERE id = ?").bind(store, carrier, user_id).run()
            return Response.new(json.dumps({"message": "OK"}), headers=headers)

        return Response.new("Not Found", status=404, headers=headers)

    except Exception as e:
        import traceback
        return Response.new(json.dumps({"error": str(e), "traceback": traceback.format_exc()}), status=500, headers=headers)