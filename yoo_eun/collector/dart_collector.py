import requests
import os
from dotenv import load_dotenv
from datetime import datetime, timedelta

load_dotenv()
DART_API_KEY = os.getenv("DART_API_KEY")

def fetch_disclosures():
    end_date = datetime.today()
    start_date = end_date - timedelta(days=89)

    url = "https://opendart.fss.or.kr/api/list.json"
    params = {
        "crtfc_key": DART_API_KEY,
        "bgn_de": start_date.strftime("%Y%m%d"),
        "end_de": end_date.strftime("%Y%m%d"),
        "page_no": 1,
        "page_count": 20
    }

    try:
        response = requests.get(url, params=params, timeout=5)
        data = response.json()

        if data.get("status") == "013":
            print("⚠️ 인증키 오류")
            return []

        if data.get("status") != "000":
            print(f"❌ 오류 발생: {data.get('message')}")
            return []

        return data.get("list", [])

    except Exception as e:
        print(f"❌ DART API 요청 실패: {e}")
        return []

def format_disclosure(entry):
    return {
        "title": f"[{entry['corp_name']}] {entry['report_nm']}",
        "url": f"https://dart.fss.or.kr/dsaf001/main.do?rcpNo={entry['rcept_no']}",
        "summary": f"{entry['rcept_dt']} 접수된 공시",
        "published_at": entry["rcept_dt"],
        "source": "DART"
    }