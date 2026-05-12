import pandas as pd


#base_path = os.path.dirname(os.path.abspath(__file__))
json_path = '/Users/seulbinlee/Antigravity/crawling_result.json'

df = pd.read_json(json_path)

# 2. 'promotions' 리스트 데이터를 분리하여 새 컬럼 생성
# promotions: ['행사유형', '카테고리', '날짜'] 순서임을 반영
df['event_type'] = df['promotions'].str[0]  # 리스트의 첫 번째: 1+1, 2+1 등
df['category'] = df['promotions'].str[1]    # 리스트의 두 번째: 과자, 음료 등

# 1. 행사 유형별 (1+1, 2+1, 할인 등) 추출
if 'event_type' in df.columns:
    print("\n[행사 유형별 상품 수]")
    print(df['event_type'].value_counts())

# 2. 상품 종류별 (음료, 과자, 간편식사 등) 추출
if 'category' in df.columns:
    print("\n[상품 종류별(카테고리) 상품 수]")
    print(df['category'].value_counts())

# 3. 편의점별 행사 현황
if 'store' in df.columns:
    print("\n[편의점별 전체 행사 상품 수]")
    print(df['shop'].value_counts())

# 4. 교차 분석: 편의점별로 어떤 행사를 많이 하나?
print("\n[편의점 x 행사유형 교차 분석]")
cross_tab = pd.crosstab(df['shop'], df['event_type'])
print(cross_tab)