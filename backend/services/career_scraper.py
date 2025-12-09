# # backend/services/career_scraper.py

# import os
# import requests
# import xml.etree.ElementTree as ET
# from dotenv import load_dotenv
# import random
# from datetime import datetime, timedelta

# load_dotenv()

# WORKNET_AUTH_KEY = os.getenv("WORKNET_API_KEY")
# API_URL = "http://openapi.work.go.kr/opi/opi/opia/wantedApi.do"

# def get_mock_jobs(keyword):
#     """
#     🚧 [개발용] API 승인 대기 중에 사용할 가짜(Mock) 데이터 생성기
#     """
#     print(f"⚠️ [Mock Mode] '{keyword}'에 대한 가짜 데이터를 생성합니다.")
    
#     mock_data = []
#     # 그럴싸한 가짜 데이터 목록
#     titles = [
#         f"{keyword} 백엔드 개발자 채용 (신입/경력)", 
#         f"[판교] {keyword} 기반 대용량 트래픽 처리 담당자",
#         f"AI 솔루션 {keyword} 엔지니어 모집",
#         f"금융권 {keyword} 서버 개발자 (여의도)",
#         f"유니콘 스타트업 {keyword} 풀스택 개발자"
#     ]
#     companies = ["네카라쿠배", "당토직야", "몰두센", "우아한형제들", "비바리퍼블리카"]
#     locations = ["서울 강남구", "경기 성남시", "서울 영등포구", "재택근무", "서울 송파구"]
    
#     for i in range(5):
#         mock_data.append({
#             "title": titles[i],
#             "company": companies[i],
#             "url": "https://www.work.go.kr", # 클릭 시 이동할 가짜 링크
#             "location": locations[i],
#             "job_type": "연봉 4,000만원 이상",
#             "close_date": (datetime.now() + timedelta(days=14)).strftime("%Y-%m-%d"),
#             "source": "Worknet (Mock)" # 가짜임을 표시 (프론트에서 배지 표시용)
#         })
#     return mock_data

# def parse_worknet_xml(xml_string):
#     """
#     워크넷 XML 응답을 파싱하여 딕셔너리 리스트로 변환
#     """
#     try:
#         root = ET.fromstring(xml_string)
#     except ET.ParseError:
#         return []

#     jobs = []
#     # <wanted> 태그가 채용공고 하나입니다.
#     for wanted in root.findall(".//wanted"):
#         try:
#             title = wanted.find("title").text or ""
#             company = wanted.find("businoNm").text or "Unknown"
#             url = wanted.find("wantedInfoUrl").text or ""
#             salary = wanted.find("salTpNm").text or ""
#             region = wanted.find("region").text or ""
#             close_date = wanted.find("closeDt").text or ""
            
#             job = {
#                 "title": title,
#                 "company": company,
#                 "url": url,
#                 "location": region,
#                 "job_type": salary,   
#                 "close_date": close_date,
#                 "source": "Worknet"
#             }
#             jobs.append(job)
#         except AttributeError:
#             continue
            
#     return jobs

# def crawl_career_all(keyword="파이썬", limit_per_site=20):
#     """
#     워크넷 API를 호출하되, 실패 시 Mock 데이터를 반환합니다.
#     """
#     # 1. 키가 없으면 바로 Mock 리턴
#     if not WORKNET_AUTH_KEY:
#         print("❌ .env에 WORKNET_API_KEY가 없습니다. (Mock 사용)")
#         return get_mock_jobs(keyword)

#     params = {
#         "authKey": WORKNET_AUTH_KEY,
#         "callTp": "L",       # List
#         "returnType": "XML",
#         "startPage": 1,
#         "display": limit_per_site,
#         "keyword": keyword,
#         "occupation": "024"  # IT 직종
#     }

#     print(f"📡 [Worknet] API 요청: {keyword}")
    
#     try:
#         res = requests.get(API_URL, params=params, timeout=5)
        
#         if res.status_code == 200:
#             # 2. 에러 메시지 체크 (권한 없음 002 에러 등)
#             if "<error>" in res.text or "<message>" in res.text:
#                 print(f"🚨 API 권한 대기 중 (002 Error). Mock 데이터를 사용합니다.")
#                 return get_mock_jobs(keyword)

#             jobs = parse_worknet_xml(res.text)
            
#             # 3. 데이터가 0건이어도 개발을 위해 Mock 리턴
#             if not jobs:
#                 print(f"ℹ️ 검색 결과가 없어 Mock 데이터를 반환합니다.")
#                 return get_mock_jobs(keyword)

#             print(f"✅ [Worknet] '{keyword}' 관련 {len(jobs)}건 수집 완료")
#             return jobs
#         else:
#             print(f"❌ API Error: {res.status_code}")
#             return get_mock_jobs(keyword)
            
#     except Exception as e:
#         print(f"❌ Connection Error: {e}")
#         return get_mock_jobs(keyword)