import requests
from bs4 import BeautifulSoup
import time

def crawl_convenience_store(shop_name, max_pages=3):
    """
    지정된 편의점(GS25, CU 등)의 할인 품목을 크롤링합니다.
    """
    base_url = "https://xn--vf4b15j1pa468argc.com/ajax.item_list.php"
    items = []
    
    for page in range(1, max_pages + 1):
        params = {
            "mode": "list",
            "item_shop": shop_name,
            "item_category": "전체",
            "item_type": "전체",
            "order_by": "item_price1",
            "serche_text": "",
            "page_num": page
        }
        
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
        
        try:
            response = requests.get(base_url, params=params, headers=headers)
            response.raise_for_status()
            
            text_data = response.text.strip()
            if not text_data or "검색조건에 일치하는 상품이 없습니다" in text_data:
                break
                
            soup = BeautifulSoup(text_data, 'html.parser')
            
            li_elements = soup.find_all('li', class_='items')
            if not li_elements:
                break
                
            for li in li_elements:
                name_tag = li.find('p', class_='item_name')
                price_tag = li.find('span', class_='price1')
                
                # 할인 뱃지 (1+1, 2+1 등)
                icon_box = li.find('div', class_='icon_box')
                icons = [span.text.strip() for span in icon_box.find_all('span')] if icon_box else []
                
                if name_tag and price_tag:
                    name = name_tag.text.strip()
                    price_text = price_tag.text.strip().replace('원', '').replace(',', '').strip()
                    
                    items.append({
                        'shop': shop_name,
                        'name': name,
                        'price': int(price_text) if price_text.isdigit() else price_text,
                        'promotions': icons
                    })
            
            # 서버 부하를 줄이기 위한 약간의 대기 시간
            time.sleep(0.5)
            
        except Exception as e:
            print(f"Error fetching page {page} for {shop_name}: {e}")
            break
            
    return items

if __name__ == "__main__":
    import json
    
    all_data = []

    print("===== GS25 할인 품목 크롤링 =====")
    gs25_data = crawl_convenience_store("GS25", max_pages=135)
    for item in gs25_data:
        print(item)
    all_data.extend(gs25_data)
        
    print("\n===== CU 할인 품목 크롤링 =====")
    cu_data = crawl_convenience_store("CU", max_pages=123)
    for item in cu_data:
        print(item)
    all_data.extend(cu_data)

    # 크롤링 결과를 JSON 파일로 저장
    with open('crawling_result.json', 'w', encoding='utf-8') as f:
        json.dump(all_data, f, ensure_ascii=False, indent=4)
        
    print(f"\n✅ 크롤링 완료! 총 {len(all_data)}개의 데이터가 'crawling_result.json' 파일에 저장되었습니다.")


