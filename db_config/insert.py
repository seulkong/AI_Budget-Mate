import pandas as pd
from sqlalchemy import create_engine

def upload_to_postgres():
    try:
        # 1. 파일 읽기
        df_cards = pd.read_csv('Card.csv')
        df_telecom = pd.read_csv('Telecom.csv')

        # 2. Postgres 접속 정보
        db_config = {
            'user': 'seulbinlee',
            'password': '',  
            'host': 'localhost',
            'port': '5432',
            'database': 'young_saver_db'
        }
        
        # 연결 문자열 생성
        engine = create_engine(
            f"postgresql://{db_config['user']}@{db_config['host']}:{db_config['port']}/{db_config['database']}",
            client_encoding='utf8'
        )

        # 3. 데이터 DBeaver에 업로드
        df_cards.to_sql('card_benefits', engine, if_exists='replace', index=False)
        df_telecom.to_sql('telecom_benefits', engine, if_exists='replace', index=False)

        print("[성공] Postgres DB 연결 및 테이블 생성이 완료되었습니다!")

    except Exception as e:
        print(f"[오류] 업로드 중 문제가 발생했습니다: {e}")
        print("팁: 'young_saver_db'라는 이름의 데이터베이스가 미리 생성되어 있는지 확인해 주세요!")

if __name__ == "__main__":
    upload_to_postgres()