import pandas as pd

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
import time
from bs4 import BeautifulSoup

service = Service(ChromeDriverManager().install())
driver = webdriver.Chrome(service=service)

region = '서울'
# 특정 카테고리 지정
category = ['한식', '중식', '일식', '양식', '아시안', '해산물', '치킨', '피자', '버거', '도시락', '샐러드', '샌드위치', '맥시칸', '채식', '분식', '카페', '디저트', '베이커리', '간식', '죽']
# 다이닝코드 데이터 크롤링
url = f'https://www.diningcode.com/list.dc?query={region}%20'

df_list = []

# 간단한 데이터 추가를 위해 각 카테고리마다 20곳의 음식점 데이터를 가져옴
for cat in category[:] :
    driver.get(url + cat)
    time.sleep(3)

    soup = BeautifulSoup(driver.page_source, 'html.parser')

    # 더 간단한 셀렉터로 시도
    datas = soup.select('div.Poi__List__Wrap')

    # 디버깅: datas가 비어있는지 확인
    print(f"\n카테고리: {cat}")
    print(f"찾은 데이터 개수: {len(datas)}")

    if len(datas) == 0:
        # 다른 셀렉터들 시도
        datas = soup.select('.Poi__List__Wrap')
        print(f"두 번째 시도 - 찾은 데이터 개수: {len(datas)}")

        if len(datas) == 0:
            # 페이지 구조 확인을 위해 일부 HTML 출력
            print("페이지에서 찾을 수 있는 주요 클래스들:")
            divs = soup.find_all('div', limit=20)
            for div in divs:
                if div.get('class'):
                    print(f"  클래스: {div.get('class')}")

    # Marker 클래스를 가진 a 태그에서 위도/경도 정보 추출
    point_datas = soup.select("a.Marker")

    print(f"찾은 마커 개수: {len(point_datas)}")

    # 마커 인덱스를 추적하기 위한 카운터
    marker_index = 0

    for i, data in enumerate(datas):
        header = [ h.text.split(' ', 1)[1] for h in data.select('h2') ]
        score = [ float(s.text) for s in data.select('.score-text') ]
        count = [ int(c.text[1:-2]) for c in data.select('.count-text') ]

        # header, score, count는 리스트이므로 각 레스토랑마다 위치 정보를 매칭
        num_restaurants = len(header)
        print(f"\ndata[{i}] 안의 레스토랑 개수: {num_restaurants}")

        if header and score and count:  # 데이터가 있는지 확인
            # 각 레스토랑마다 위치 정보 리스트 생성
            latitudes = []
            longitudes = []

            for j in range(num_restaurants):
                if marker_index < len(point_datas):
                    point_data = point_datas[marker_index]
                    lat = point_data.get('data-lat')
                    lng = point_data.get('data-lng')
                    latitudes.append(lat)
                    longitudes.append(lng)
                    # print(f"  [{j}] {header[j][:20]}... - 위도: {lat}, 경도: {lng}")
                    marker_index += 1
                else:
                    latitudes.append(None)
                    longitudes.append(None)

            temp_df = pd.DataFrame({
                'rest': header,
                'category': cat,
                'score': score,
                'count': count,
                'latitude': latitudes,
                'longitude': longitudes
            })
            print(f"추가된 레스토랑 개수: {len(temp_df)}")
            df_list.append(temp_df)
        else:
            print("경고: 빈 데이터 건너뜀")

df = pd.concat(df_list, ignore_index=True) if df_list else pd.DataFrame(columns=['rest', 'category', 'score', 'count', 'latitude', 'longitude'])

print(df.info())

# CSV 파일로 저장
df.to_csv('./data/seoul_restaurant.csv', index=False, encoding='utf-8')