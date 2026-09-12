import pandas as pd
import streamlit as st
import plotly.express as px

DATA_URL = "https://raw.githubusercontent.com/greatsong/modudata/main/data/kobis_daily.csv"

st.set_page_config(
    page_title="영화 데이터 그래프 도감 1 - 시간",
    page_icon="🎬",
    layout="wide",
)

st.title("영화 데이터 그래프 도감 1 - 시간")
st.write("영화별 일일 관객 수가 시간에 따라 어떻게 변하는지 살펴봅니다.")

@st.cache_data
def load_data():
    df = pd.read_csv(DATA_URL)
    df.columns = ["날짜", "순위", "영화코드", "영화명", "일관객", "누적관객", "스크린수", "상영횟수"]

    # 날짜: 하이픈 없는 8자리 숫자 → 실제 날짜형
    df["날짜"] = pd.to_datetime(df["날짜"].astype(str), format="%Y%m%d", errors="coerce")

    # 숫자형 열 정리
    for col in ["순위", "일관객", "누적관객", "스크린수", "상영횟수"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    return df.dropna(subset=["날짜", "영화명", "일관객"])


try:
    df = load_data()
except Exception as e:
    st.error("데이터를 불러오는 중 문제가 발생했습니다.")
    st.exception(e)
    st.stop()


# ============================================================
# 그래프 1
# ============================================================
st.header("그래프 1. 영화별 날짜에 따른 일관객 변화")

movies = sorted(df["영화명"].dropna().unique())
selected_movie = st.selectbox("영화를 선택하세요.", movies)

movie_df = (
    df[df["영화명"] == selected_movie]
    .sort_values("날짜")
    .copy()
)

fig = px.line(
    movie_df,
    x="날짜",
    y="일관객",
    markers=True,
    labels={
        "날짜": "날짜",
        "일관객": "일관객 수",
    },
    title=f"「{selected_movie}」의 날짜별 일관객 변화",
)

fig.update_traces(
    hovertemplate="날짜: %{x|%Y-%m-%d}<br>관객 수: %{y:,}명<extra></extra>"
)

fig.update_layout(
    hovermode="x unified",
    yaxis_tickformat=",",
    height=500,
)

st.plotly_chart(fig, use_container_width=True)

st.markdown("**이 그래프로 알 수 있는 것:**")
st.text_input(
    "문구를 입력하세요.",
    placeholder="예: 개봉일 이후 관객 수가 증가하다가 점차 감소하는 추세를 확인할 수 있다.",
    key="graph1_note",
    label_visibility="collapsed",
)


# ============================================================
# 앞으로 추가할 그래프 영역
# ============================================================
st.divider()
st.header("그래프 2")
st.info("앞으로 추가할 그래프를 이 구역에 넣으면 됩니다.")

st.divider()
st.header("그래프 3")
st.info("앞으로 추가할 그래프를 이 구역에 넣으면 됩니다.")
