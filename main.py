# 날짜를 골라 보는 박스오피스 — main.py에 이어 붙일 부분
import datetime
import pandas as pd
import requests
import streamlit as st

KST = datetime.timezone(datetime.timedelta(hours=9))
어제 = datetime.datetime.now(KST).date() - datetime.timedelta(days=1)
고른날 = st.date_input("날짜를 고르세요", value=어제, max_value=어제)

URL = "https://www.kobis.or.kr/kobisopenapi/webservice/rest/boxoffice/searchDailyBoxOfficeList.json"


@st.cache_data(ttl=3600)
def fetch(day_text):
    res = requests.get(URL, params={"key": st.secrets["KOBIS_KEY"], "targetDt": day_text}, timeout=20)
    answer = res.json().get("boxOfficeResult")
    return answer["dailyBoxOfficeList"] if answer else []


movies = fetch(고른날.strftime("%Y%m%d"))
if not movies:
    st.info("그날은 아직 집계 전입니다.")
    st.stop()

표 = pd.DataFrame([{
    "순위": int(m["rank"]),
    "영화명": ("🏆 " if int(m["audiAcc"]) >= 1_000_000 else "") + m["movieNm"],
    "순위 변화": ("🔺" + str(int(m["rankInten"])) if int(m["rankInten"]) > 0
                 else "🔻" + str(-int(m["rankInten"])) if int(m["rankInten"]) < 0 else "—"),
    "관객수": int(m["audiCnt"]),
    "누적관객": int(m["audiAcc"]),
} for m in movies])
st.dataframe(표, hide_index=True)
st.caption("🔺 오른 영화 · 🔻 내린 영화 · 🏆 누적 100만 명을 넘은 영화")
