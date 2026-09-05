import pandas as pd
import plotly.express as px
import streamlit as st

# 페이지 기본 설정
st.set_page_config(
    page_title="서울 100년 기온 변화 추이",
    page_icon="🌡️",
    layout="wide",
)

# 데이터 불러오기 함수 (캐싱 처리로 성능 최적화)
DATA_URL = (
    "https://raw.githubusercontent.com/greatsong/modudata/main/data/seoul.csv"
)


@st.cache_data
def load_data():
    # CSV 데이터 로드
    df = pd.read_csv(DATA_URL)

    # 컬럼명 정제 (공백 제거)
    df.columns = df.columns.str.strip()

    # 날짜 데이터 변환 및 연도 추출
    df["날짜"] = pd.to_datetime(df["날짜"])
    df["연도"] = df["날짜"].dt.year

    # '평균기온(℃)' 또는 '평균기온' 컬럼 찾기
    temp_col = [col for col in df.columns if "평균기온" in col][0]

    # 결측치 제거 후 연도별 평균기온 계산
    df_clean = df.dropna(subset=[temp_col])
    yearly_avg = (
        df_clean.groupby("연도")[temp_col].mean().reset_index()
    )
    yearly_avg.columns = ["연도", "연평균기온"]

    return yearly_avg


# 앱 타이틀 및 설명
st.title("🌡️ 지난 100년간 서울의 연평균 기온 변화")
st.markdown(
    """
서울의 기후 변화 데이터를 한눈에 확인해보세요. 
데이터 출처: [modudata GitHub](https://github.com/greatsong/modudata)
"""
)

try:
    yearly_df = load_data()

    # 주요 지표 (Metric) 표시
    min_year = int(yearly_df["연도"].min())
    max_year = int(yearly_df["연도"].max())
    first_temp = yearly_df.iloc[0]["연평균기온"]
    latest_temp = yearly_df.iloc[-1]["연평균기온"]
    temp_diff = latest_temp - first_temp

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("조회 기간", f"{min_year}년 ~ {max_year}년")
    col2.metric(f"{min_year}년 연평균 기온", f"{first_temp:.1f} ℃")
    col3.metric(f"{max_year}년 연평균 기온", f"{latest_temp:.1f} ℃")
    col4.metric(
        "기온 변화 폭",
        f"{temp_diff:+.1f} ℃",
        delta_color="inverse" if temp_diff < 0 else "normal",
    )

    st.divider()

    # Plotly 시각화 그래프
    fig = px.line(
        yearly_df,
        x="연도",
        y="연평균기온",
        title="서울 연도별 연평균 기온 추이",
        labels={"연도": "연도 (Year)", "연평균기온": "연평균 기온 (℃)"},
        markers=True,
    )

    # 추세선 추가 및 스타일 설정
    fig.update_traces(
        line_color="#E74C3C",
        line_width=2,
        marker=dict(size=4),
        hovertemplate="<b>%{x}년</b><br>연평균 기온: %{y:.2f}℃",
    )

    fig.update_layout(
        hovermode="x unified",
        xaxis=dict(showgrid=True, gridcolor="#EAEAEA"),
        yaxis=dict(showgrid=True, gridcolor="#EAEAEA"),
        height=500,
    )

    st.plotly_chart(fig, use_container_width=True)

    # 데이터 테이블 원본 보기 옵션
    with st.expander("📊 연도별 평균 기온 데이터 보기"):
        st.dataframe(
            yearly_df.style.format({"연도": "{:.0f}", "연평균기온": "{:.2f}℃"}),
            use_container_width=True,
        )

except Exception as e:
    st.error(f"데이터를 불러오는 중 오류가 발생했습니다: {e}")
