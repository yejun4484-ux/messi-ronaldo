```python
import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go

# --------------------------------------------------
# 기본 설정
# --------------------------------------------------
st.set_page_config(
    page_title="기온 예측기",
    page_icon="🌡️",
    layout="wide",
)

DATA_URL = (
    "https://raw.githubusercontent.com/greatsong/modudata/"
    "bb860932644270ad1199f10d3e7670e30231bce4/data/seoul.csv"
)

BASE_YEAR = 1908
LAST_CLASS_YEAR = 2025
MIN_OBSERVATION_DAYS = 300


# --------------------------------------------------
# 데이터 불러오기
# --------------------------------------------------
@st.cache_data
def load_data():
    df = pd.read_csv(DATA_URL, encoding="utf-8-sig")

    df["날짜"] = pd.to_datetime(df["날짜"], errors="coerce")
    df["평균기온"] = pd.to_numeric(df["평균기온"], errors="coerce")

    df = df.dropna(subset=["날짜", "평균기온"])

    df["연도"] = df["날짜"].dt.year

    # 2025년까지의 데이터만 사용
    df = df[df["연도"] <= LAST_CLASS_YEAR]

    # 연도별 평균기온과 관측일수
    annual = (
        df.groupby("연도")
        .agg(
            연평균기온=("평균기온", "mean"),
            관측일수=("평균기온", "count"),
        )
        .reset_index()
    )

    # 관측일수가 300일 미만인 연도 제외
    annual = annual[
        annual["관측일수"] >= MIN_OBSERVATION_DAYS
    ].copy()

    # 1908년부터 지난 연수
    annual["1908년부터_지난_연수"] = (
        annual["연도"] - BASE_YEAR
    )

    return annual


annual = load_data()


# --------------------------------------------------
# 전체 기간 회귀
# --------------------------------------------------
x_all = annual["1908년부터_지난_연수"].to_numpy()
y_all = annual["연평균기온"].to_numpy()

slope_all, intercept_all = np.polyfit(
    x_all,
    y_all,
    1
)

# 1년당 변화량 → 100년당 변화량
slope_all_100 = slope_all * 100

correlation = annual["연도"].corr(
    annual["연평균기온"]
)

start_year = int(annual["연도"].min())
end_year = int(annual["연도"].max())
year_count = len(annual)


# --------------------------------------------------
# 최근 20년 회귀
# --------------------------------------------------
# 사용 가능한 마지막 연도부터 20년
recent_start_year = end_year - 19

recent = annual[
    annual["연도"] >= recent_start_year
].copy()

x_recent = (
    recent["연도"] - recent_start_year
).to_numpy()

y_recent = recent["연평균기온"].to_numpy()

slope_recent, intercept_recent = np.polyfit(
    x_recent,
    y_recent,
    1
)

# 1년당 변화량 → 100년당 변화량
slope_recent_100 = slope_recent * 100


# --------------------------------------------------
# 제목
# --------------------------------------------------
st.title("🌡️ 기온 예측기")

st.write(
    "서울의 연도별 평균기온을 이용해 장기간의 기온 변화와 "
    "최근 20년의 기온 변화 추세를 비교합니다."
)


# ------------------------
```
