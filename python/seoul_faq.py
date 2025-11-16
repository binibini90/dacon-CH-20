import time
import pandas as pd
import os
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

URL = "https://korean.visitseoul.net/faq"

def get_faq_data():
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service)
    wait = WebDriverWait(driver, 10)
    
    all_data = []

    try:
        driver.get(URL)
        driver.maximize_window()
        print("사이트 접속 완료")
        time.sleep(3)

        # 카테고리 버튼 텍스트 가져오기 (onclick 함수 호출 방식 사용)
        categories = driver.find_elements(By.CSS_SELECTOR, "div.tag-element--faq a")
        category_list = []
        
        for cat in categories:
            cat_text = cat.text.strip()
            onclick = cat.get_attribute("onclick")
            if cat_text and cat_text != "전체":
                # onclick에서 카테고리 ID 추출 (ctgrySearch('1') 형태)
                category_list.append((cat_text, onclick))

        print(f"찾은 카테고리: {[c[0] for c in category_list]}")

        # 각 카테고리별로 크롤링
        for cat_name, onclick_value in category_list:
            print(f"\n카테고리 '{cat_name}' 크롤링 중...")
            
            # JavaScript onclick 함수 직접 호출
            driver.execute_script(onclick_value)
            time.sleep(2)
            
            page = 1
            while True:
                try:
                    # FAQ 리스트 로드 대기
                    faq_list = wait.until(EC.presence_of_all_elements_located(
                        (By.CSS_SELECTOR, "div.faq-list-cont")))
                    
                    print(f"  페이지 {page}: {len(faq_list)}개 FAQ 발견")
                    
                    for faq in faq_list:
                        try:
                            # 질문 추출
                            question = faq.find_element(By.CSS_SELECTOR, "span.text-cont").text.strip()
                            
                            # 스크롤 및 질문 클릭
                            driver.execute_script("arguments[0].scrollIntoView({block:'center'});", faq)
                            time.sleep(0.3)
                            
                            # 질문 링크 클릭
                            question_link = faq.find_element(By.CSS_SELECTOR, "div.faq-q a")
                            driver.execute_script("arguments[0].click();", question_link)
                            time.sleep(0.5)
                            
                            # 답변 div 찾기
                            answer_div = faq.find_element(By.CSS_SELECTOR, "div.faq-a")
                            answer = answer_div.text.replace("A.", "").replace("(답변 아이콘)", "").strip()
                            
                            all_data.append([cat_name, question, answer])
                            
                        except Exception as e:
                            print(f"    FAQ 처리 중 오류: {e}")
                            continue
                    
                    # 다음 페이지 버튼 찾기
                    try:
                        paging_links = driver.find_elements(By.CSS_SELECTOR, "div.paging-lst a")
                        next_btn = None
                        
                        for link in paging_links:
                            if link.get_attribute("class") == "on":
                                # 현재 페이지 다음 버튼 찾기
                                next_siblings = driver.execute_script(
                                    "return arguments[0].nextElementSibling;", link)
                                if next_siblings:
                                    next_btn = driver.find_element(
                                        By.XPATH, 
                                        f"//div[@class='paging-lst']/a[@class='on']/following-sibling::a[1]"
                                    )
                                    break
                        
                        if next_btn:
                            driver.execute_script("arguments[0].click();", next_btn)
                            time.sleep(2)
                            page += 1
                        else:
                            break
                            
                    except Exception as e:
                        print(f"  페이지 {page} 다음 페이지 없음")
                        break
                        
                except Exception as e:
                    print(f"  페이지 {page} 처리 중 오류: {e}")
                    break

    except Exception as e:
        print(f"크롤링 중 오류 발생: {e}")
        
    finally:
        driver.quit()

    return all_data

if __name__ == "__main__":
    data = get_faq_data()
    
    if data:
        df = pd.DataFrame(data, columns=["Category", "Question", "Answer"])
        # 현재 파일 위치 기준으로 data 폴더 경로 설정
        current_dir = os.path.dirname(os.path.abspath(__file__))
        parent_dir = os.path.dirname(current_dir)
        output_file = os.path.join(parent_dir, "data", "seoul_faq.csv")
        df.to_csv(output_file, index=False, encoding="utf-8-sig")
        print(f"\n✓ CSV 저장 완료! ({len(data)}개 FAQ)")
        print(f"파일 경로: {output_file}")
        print(f"\n첫 5개 데이터:")
        print(df.head())
    else:
        print("크롤링된 데이터가 없습니다.")
        
