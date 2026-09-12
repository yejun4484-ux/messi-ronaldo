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
# 그래프 2
# ============================================================
st.divider()
st.header("그래프 2. 일관객 합계 상위 5편의 날짜별 변화")

top5_movies = (
    df.groupby("영화명", as_index=False)["일관객"]
    .sum()
    .sort_values("일관객", ascending=False)
    .head(5)["영화명"]
    .tolist()
)

top5_df = (
    df[df["영화명"].isin(top5_movies)]
    .sort_values("날짜")
    .copy()
)

fig2 = px.line(
    top5_df,
    x="날짜",
    y="일관객",
    color="영화명",
    markers=True,
    labels={
        "날짜": "날짜",
        "일관객": "일관객 수",
        "영화명": "영화",
    },
    title="일관객 합계 상위 5편의 날짜별 일관객 변화",
)

fig2.update_traces(
    hovertemplate="날짜: %{x|%Y-%m-%d}<br>관객 수: %{y:,}명<extra>%{fullData.name}</extra>"
)

fig2.update_layout(
    hovermode="x unified",
    yaxis_tickformat=",",
    height=550,
    legend_title_text="영화 (클릭하여 켜기/끄기)",
)

st.plotly_chart(fig2, use_container_width=True)

st.markdown("**이 그래프로 알 수 있는 것:**")
st.text_input(
    "문구를 입력하세요.",
    placeholder="예: 일관객 합계가 큰 영화들의 흥행 추이를 날짜별로 비교할 수 있다.",
    key="graph2_note",
    label_visibility="collapsed"
)

# ============================================================
# 그래프 3
# ============================================================
st.divider()
st.header("그래프 3. 날짜별 10위권 일관객 합계")

daily_total = (
    df.groupby("날짜", as_index=False)["일관객"]
    .sum()
    .sort_values("날짜")
)

top_3_days = daily_total.nlargest(3, "일관객").sort_values("날짜")

fig3 = px.area(
    daily_total,
    x="날짜",
    y="일관객",
    labels={"날짜": "날짜", "일관객": "10위권 일관객 합계"},
    title="날짜별 10위권 일관객 합계",
)

fig3.update_traces(
    hovertemplate="날짜: %{x|%Y-%m-%d}<br>관객 수: %{y:,}명<extra></extra>"
)

fig3.add_scatter(
    x=top_3_days["날짜"],
    y=top_3_days["일관객"],
    mode="markers+text",
    text=top_3_days["날짜"].dt.strftime("%Y-%m-%d"),
    textposition="top center",
    marker=dict(size=10),
    name="합계 상위 3일",
    hovertemplate="날짜: %{x|%Y-%m-%d}<br>관객 수: %{y:,}명<extra></extra>",
)

fig3.update_layout(
    hovermode="x unified",
    yaxis_tickformat=",",
    height=500,
    showlegend=True,
)

st.plotly_chart(fig3, use_container_width=True)

st.markdown("**이 그래프로 알 수 있는 것:**")
st.text_input(
    "문구를 입력하세요.",
    placeholder="예: 특정 날짜에 영화관 관객이 크게 몰린 시점을 확인할 수 있다.",
    key="graph3_note",
    label_visibility="collapsed",
)

# ============================================================
# 그래프 4
# ============================================================
st.divider()
st.header("그래프 4. 영화별 기간 일관객 TOP 10")

movie_summary = (
    df.groupby("영화명")
    .agg(
        기간_일관객_합계=("일관객", "sum"),
        10위권_등장일수=("날짜", "nunique"),
    )
    .sort_values("기간_일관객_합계", ascending=False)
    .head(10)
    .sort_values("기간_일관객_합계", ascending=True)
    .reset_index()
)

fig4 = px.bar(
    movie_summary,
    x="기간_일관객_합계",
    y="영화명",
    orientation="h",
    labels={
        "영화명": "영화",
        "기간_일관객_합계": "기간 일관객 합계",
    },
    title="영화별 기간 일관객 TOP 10",
    custom_data=["10위권_등장일수"],
)

fig4.update_traces(
    hovertemplate=(
        "영화: %{y}<br>"
        "기간 일관객 합계: %{x:,}명<br>"
        "10위권에 든 날: %{customdata[0]}일"
        "<extra></extra>"
    )
)

fig4.update_layout(
    height=550,
    xaxis_tickformat=",",
)

st.plotly_chart(fig4, use_container_width=True)

st.markdown("**이 그래프로 알 수 있는 것:**")
st.text_input(
    "문구를 입력하세요.",
    placeholder="예: 이 기간 동안 관객을 가장 많이 모은 영화들을 비교할 수 있다.",
    key="graph4_note",
    label_visibility="collapsed",
)
