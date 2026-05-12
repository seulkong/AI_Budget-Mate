import os
import pandas as pd
from sqlalchemy import create_engine, text

base_path = os.path.dirname(os.path.abspath(__file__))
json_path = os.path.join(base_path, 'crawling_result.json')

df = pd.read_json(json_path)

# 2. PostgreSQL 연결 정보
DB_URL = 'postgresql://seulbinlee@localhost:5432/postgres'

def main():
    try:
        # 데이터 로드
        if not os.path.exists(json_path):
            raise FileNotFoundError(f"'{json_path}' 파일을 찾을 수 없습니다.")
        
        print(f"데이터를 읽어오는 중: {json_path}")
        df = pd.read_json(json_path)

        # 3. 데이터 전처리 (DB 최적화)
        # promotions 리스트를 컬럼으로 분리
        df['event_type'] = df['promotions'].str[0]
        df['category'] = df['promotions'].str[1]
        df['update_month'] = df['promotions'].str[2]
        
        # DB에 넣기 힘든 리스트 타입 컬럼 삭제 및 가격 정제
        df_db = df.drop(columns=['promotions'])
        df_db['price'] = df_db['price'].astype(str).str.replace('원', '').str.replace(',', '').astype(int)
        
        # 데이터 생성 시간 추가 (탄탄한 관리를 위해 필수!)
        df_db['created_at'] = pd.Timestamp.now()

        # 4. PostgreSQL 엔진 생성 및 데이터 저장
        engine = create_engine(DB_URL)
        
        # 테이블 이름: convenience_promotions
        # if_exists='replace': 기존 데이터를 지우고 새로 생성 (초기 단계 추천)
        df_db.to_sql('convenience_promotions', engine, if_exists='replace', index=False)
        
        print(" PostgreSQL 데이터 적재 완료!")
        
        # 5. 간단한 검증 쿼리 실행
        with engine.connect() as conn:
            result = conn.execute(text("SELECT COUNT(*) FROM convenience_promotions"))
            count = result.fetchone()[0]
            print(f" 현재 DB에 저장된 총 행사 상품 수: {count}개")

    except Exception as e:
        print(f" 오류 발생: {e}")

if __name__ == "__main__":
    main()