import pandas as pd
from sqlalchemy import create_engine, text

# 1. DB 연결 설정
DB_URL = 'postgresql://seulbinlee@localhost:5432/postgres'
engine = create_engine(DB_URL)

def search_promotion_items(keyword):
    """
    상품명을 입력받아 DB에서 해당 키워드가 포함된 행사 상품을 찾아 반환합니다.
    """
    query = text("""
        SELECT shop, name, price, event_type, category 
        FROM convenience_promotions 
        WHERE name LIKE :keyword
        ORDER BY price ASC
    """)
    
    # % 키워드 % 형태로 만들어 부분 일치 검색 가능하게 함
    search_keyword = f"%{keyword}%"
    
    try:
        with engine.connect() as conn:
            # 쿼리 실행 후 결과를 데이터프레임으로 변환
            result = pd.read_sql(query, conn, params={"keyword": search_keyword})
            
            if result.empty:
                print(f" '{keyword}'에 대한 행사 상품을 찾지 못했습니다.")
            else:
                print(f" '{keyword}' 검색 결과: {len(result)}건을 찾았습니다.")
                print("-" * 50)
                print(result)
            return result
            
    except Exception as e:
        print(f"검색 중 오류 발생: {e}")
        return None

# 2. 실행 테스트
if __name__ == "__main__":
    user_input = input("찾으시는 상품명을 입력하세요 : ")
    search_promotion_items(user_input)