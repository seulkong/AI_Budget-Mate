import json
from js import Response, Headers, Object

async def on_fetch(request, env):
    # CORS 헤더 설정
    headers = Headers.new()
    headers.set("Access-Control-Allow-Origin", "*")
    headers.set("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
    headers.set("Access-Control-Allow-Headers", "*")
    headers.set("Content-Type", "application/json")
    
    method = request.method
    url = request.url
    path = "/" + "/".join(url.split("/")[3:])
    if "?" in path: path = path.split("?")[0]

    if method == "OPTIONS":
        return Response.new("", status=204, headers=headers)

    try:
        if path == "/search" and method == "POST":
            js_data = await request.json()
            data = js_data.to_py()
            
            item_name = data.get("item_name", "").strip()
            user_style = data.get("user_style", "health")
            user_store = data.get("user_store", "GS25")
            user_telecom = str(data.get("user_telecom", "none")).upper().strip()
            user_telecom_tier = str(data.get("user_telecom_tier", "low")).lower().strip()
            user_card = str(data.get("user_card", "none")).strip()

            crawling_raw = await env.CRAWLING_KV.get("crawling_result.json")
            crawling_data = json.loads(crawling_raw) if crawling_raw else []

            recommend_keywords = ['추천', '뭐가', '뭐있어', '보여줘', '핫한', '골라줘', '행사', '세일']
            is_recommend = any(kw in item_name for kw in recommend_keywords)
            search_results = [i for i in crawling_data if item_name in i.get('name', '')]
            
            # 리스트 응답
            if is_recommend or (len(search_results) > 1 and item_name not in [i['name'] for i in search_results]):
                options = []
                exclude_kws = ['쏘피', '화이트', '바디피트', '샴푸', '린스', '치약', '칫솔', '비누', '세제', '휴지', '건전지']
                
                if is_recommend:
                    style_keywords = {
                        'health': ['닭가슴살', '프로틴', '단백질', '제로', '슈거', '샐러드', '견과', '계란', '반숙', '두유', '곤약', '비타민', '생수'],
                        'dessert': ['초코', '쿠키', '케이크', '푸딩', '마카롱', '젤리', '구미', '사탕', '캔디', '아이스크림', '달콤'],
                        'trend': ['마라', '요아정', '두바이', '신상', '대란', '인기', '불닭', '치즈']
                    }
                    kws = style_keywords.get(user_style, [])
                    for item in crawling_data:
                        name = item.get('name', '')
                        if any(ex in name for ex in exclude_kws): continue
                        if any(k in name for k in kws) or ('1+1' in str(item.get('promotions', ''))):
                             options.append(item.get('name'))
                else:
                    options = [i['name'] for i in search_results]
                
                import random
                options = list(dict.fromkeys(options))
                random.shuffle(options)
                options = options[:15]
                
                if options:
                    return Response.new(json.dumps({"type": "list", "message": "고객님의 스타일에 딱 맞는 추천 리스트를 가져왔어요! ✨", "options": options}), headers=headers)

            # 단일 상품 응답
            if not search_results:
                return Response.new(json.dumps({"message": f"아쉽게도 '{item_name}' 상품은 현재 행사 중이 아니에요."}), headers=headers)
            
            best_item = search_results[0]
            exact_match = [i for i in search_results if i['name'] == item_name]
            if exact_match: best_item = exact_match[0]

            base_price = int(str(best_item.get('price', '0')).replace(',', '').replace('원', ''))
            shop = best_item.get('shop', 'GS25').upper()
            
            final_price = base_price
            discount_details = []
            
            promo = str(best_item.get('promotions', ''))
            if '1+1' in promo:
                final_price = base_price / 2
                discount_details.append(f"• [행사] 1+1 적용 (개당 -{int(base_price/2):,}원)")
            elif '2+1' in promo:
                final_price = (base_price * 2) / 3
                discount_details.append(f"• [행사] 2+1 적용 (3개 구매 시 개당 -{int(base_price/3):,}원)")
            else:
                discount_details.append("• [행사] 진행 중인 증정 행사 없음")
            
            telecom_applied = False
            try:
                telecom_raw = await env.CRAWLING_KV.get("Telecom.csv")
                if telecom_raw and user_telecom != 'NONE':
                    import csv, io
                    f = io.StringIO(telecom_raw)
                    tel_reader = list(csv.DictReader(f))
                    for row in tel_reader:
                        if row['Telecom'].upper() == user_telecom and row['Shop'].upper() == shop:
                            val_str = row['Discount_VIP'] if 'high' in user_telecom_tier else row['Discount_Normal']
                            if '%' in val_str:
                                pct = int(val_str.replace('%', '').strip())
                                amt = int(final_price * (pct / 100))
                                final_price -= amt
                                discount_details.append(f"• [통신사] {user_telecom} 멤버십 {pct}% 할인 (-{amt:,}원)")
                            elif '원' in val_str:
                                amt = int(val_str.replace('원', '').replace(',', '').strip())
                                final_price -= amt
                                discount_details.append(f"• [통신사] {user_telecom} 멤버십 할인 (-{amt:,}원)")
                            telecom_applied = True
                            break
            except: pass

            if not telecom_applied:
                if user_telecom == 'NONE': discount_details.append("• [통신사] 등록된 멤버십 없음")
                else: discount_details.append(f"• [통신사] {user_telecom}는 {shop} 제휴사가 아님")

            card_applied = False
            gs_cards = ['삼성', '국민', 'KB', 'GS', '팝']
            cu_cards = ['신한', '우리', '하나']
            if (shop == 'GS25' and any(c in user_card for c in gs_cards)) or (shop == 'CU' and any(c in user_card for c in cu_cards)):
                card_disc = int(final_price * 0.1)
                final_price -= card_disc
                discount_details.append(f"• [카드] {user_card} 제휴 10% 추가 할인 (-{card_disc:,}원)")
                card_applied = True
            else:
                discount_details.append(f"• [카드] {user_card if user_card != 'none' else '등록 카드'} 혜택 없음")

            card_recommendation = ""
            if not card_applied:
                try:
                    card_csv_raw = await env.CRAWLING_KV.get("Card.csv")
                    if card_csv_raw:
                        import csv, io
                        f = io.StringIO(card_csv_raw)
                        card_reader = list(csv.DictReader(f))
                        for row in card_reader:
                            if (shop == 'GS25' and row['Issuer'] in ['삼성카드', 'KB국민카드']) or (shop == 'CU' and row['Issuer'] in ['신한카드', '우리카드']):
                                card_recommendation = f"꿀팁! '{row['Card_Name']}'를 쓰시면 {shop}에서 {row['Benefit']} 혜택을 더 받을 수 있어요!"
                                break
                except: pass

            msg = f"'{best_item['name']}' ({shop}) 최적의 할인 조합입니다!\n\n"
            msg += f"기본 가격: {base_price:,}원\n"
            if discount_details:
                msg += "\n[적용된 할인 혜택]\n" + "\n".join(discount_details) + "\n"
            msg += f"\n✨ 최종 혜택가: {int(final_price):,}원"
            if card_recommendation: msg += "\n" + card_recommendation

            return Response.new(json.dumps({
                "type": "result",
                "message": msg,
                "shop": shop 
            }), headers=headers)

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