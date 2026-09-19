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
LAST_YEAR = 2025
MIN_DAYS = 300


# --------------------------------------------------
# 데이터 불러오기
# --------------------------------------------------
@st.cache_data
def load_data():
    df = pd.read_csv(DATA_URL, encoding="utf-8-sig")

    # 날짜 변환
    df["날짜"] = pd.to_datetime(df["날짜"], errors="coerce")

    # 숫자형 변환
    df["평균기온"] = pd.to_numeric(df["평균기온"], errors="coerce")

    # 유효한 데이터만 사용
    df = df.dropna(subset=["날짜", "평균기온"]).copy()

    # 연도 추출
    df["연도"] = df["날짜"].dt.year

    return df


# --------------------------------------------------
# 연도별 평균기온 계산
# --------------------------------------------------
@st.cache_data
def make_yearly_data(df):
    yearly = (
        df.groupby("연도")
        .agg(
            평균기온=("평균기온", "mean"),
            관측일수=("평균기온", "count"),
        )
        .reset_index()
    )

    # 기준 기간:
    # 1. 2025년 이후 제외
    # 2. 관측일수가 300일 미만인 해 제외
    # 3. 회귀의 시작 연도는 1908년
    yearly = yearly[
        (yearly["연도"] >= BASE_YEAR)
        & (yearly["연도"] <= LAST_YEAR)
        & (yearly["관측일수"] >= MIN_DAYS)
    ].copy()

    yearly = yearly.sort_values("연도").reset_index(drop=True)

    return yearly


# --------------------------------------------------
# 회귀 계산
# --------------------------------------------------
@st.cache_data
def calculate_regression(yearly):
    x = yearly["연도"].to_numpy(dtype=float) - BASE_YEAR
    y = yearly["평균기온"].to_numpy(dtype=float)

    # y = intercept + slope * (연도 - 1908)
    slope, intercept = np.polyfit(x, y, 1)

    predicted = intercept + slope * x

    # 상관계수
    correlation = np.corrcoef(x, y)[0, 1]

    return slope, intercept, correlation, predicted


# --------------------------------------------------
# 데이터 준비
# --------------------------------------------------
try:
    df = load_data()
    yearly = make_yearly_data(df)

    if len(yearly) < 2:
        st.error("회귀 분석을 수행할 수 있는 연도 데이터가 부족합니다.")
        st.stop()

    slope, intercept, correlation, predicted = calculate_regression(yearly)

except Exception as e:
    st.error(f"데이터를 불러오거나 처리하는 중 오류가 발생했습니다.\n\n{e}")
    st.stop()


# --------------------------------------------------
# 제목
# --------------------------------------------------
st.title("🌡️ 서울 기온 예측기")
st.caption(
    "서울 기상 관측자료의 연평균기온을 이용해 연도별 기온 추세를 "
    "선형회귀로 추정합니다."
)


# --------------------------------------------------
# 회귀 정보
# --------------------------------------------------
start_year = int(yearly["연도"].min())
end_year = int(yearly["연도"].max())
year_count = len(yearly)

col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric("회귀에 사용한 연도 수", f"{year_count}년")

with col2:
    st.metric("시작 연도", f"{start_year}년")

with col3:
    st.metric("끝 연도", f"{end_year}년")

with col4:
    st.metric("상관계수", f"{correlation:.3f}")


st.info(
    f"회귀 분석에는 **{start_year}년부터 {end_year}년까지**, "
    f"관측일수가 {MIN_DAYS}일 이상인 연도만 사용했습니다. "
    f"2025년 이후 데이터는 제외했습니다."
)


# --------------------------------------------------
# 연도 슬라이더
# --------------------------------------------------
selected_year = st.slider(
    "예측할 연도",
    min_value=1900,
    max_value=2100,
    value=2025,
    step=1,
)

# 회귀식으로 선택 연도의 예상 평균기온 계산
x_selected = selected_year - BASE_YEAR
predicted_temp = intercept + slope * x_selected


# --------------------------------------------------
# 선택 연도 예상 기온
# --------------------------------------------------
st.subheader(f"{selected_year}년 예상 평균기온")

st.metric(
    label="선형회귀에 따른 예상 연평균기온",
    value=f"{predicted_temp:.2f} °C",
)


# --------------------------------------------------
# Plotly 산점도 + 회귀선
# --------------------------------------------------
fig = go.Figure()

# 실제 연평균기온 산점도
fig.add_trace(
    go.Scatter(
        x=yearly["연도"],
        y=yearly["평균기온"],
        mode="markers",
        name="실제 연평균기온",
        marker=dict(
            size=7,
            color="#3498db",
            opacity=0.75,
        ),
        customdata=yearly["관측일수"],
        hovertemplate=(
            "<b>%{x}년</b><br>"
            "평균기온: %{y:.2f} °C<br>"
            "관측일수: %{customdata}일"
            "<extra></extra>"
        ),
    )
)

# 회귀선은 1900~2100년 전체 범위에 표시
regression_years = np.arange(1900, 2101)
regression_x = regression_years - BASE_YEAR
regression_temps = intercept + slope * regression_x

fig.add_trace(
    go.Scatter(
        x=regression_years,
        y=regression_temps,
        mode="lines",
        name="회귀선",
        line=dict(
            color="#e74c3c",
            width=3,
        ),
        hovertemplate=(
            "<b>%{x}년</b><br>"
            "회귀 예상기온: %{y:.2f} °C"
            "<extra></extra>"
        ),
    )
)

# 선택된 연도 표시
fig.add_trace(
    go.Scatter(
        x=[selected_year],
        y=[predicted_temp],
        mode="markers",
        name=f"{selected_year}년 예측",
        marker=dict(
            size=16,
            color="#f39c12",
            line=dict(
                color="white",
                width=2,
            ),
        ),
        hovertemplate=(
            f"<b>{selected_year}년</b><br>"
            f"예상 평균기온: {predicted_temp:.2f} °C"
            "<extra></extra>"
        ),
    )
)

fig.update_layout(
    title="서울 연평균기온과 선형회귀선",
    xaxis=dict(
        title="연도",
        tickmode="linear",
        dtick=10,
        range=[1900, 2100],
    ),
    yaxis=dict(
        title="평균기온 (°C)",
    ),
    hovermode="closest",
    legend=dict(
        orientation="h",
        yanchor="bottom",
        y=1.02,
        xanchor="left",
        x=0,
    ),
    height=600,
)

st.plotly_chart(fig, use_container_width=True)


# --------------------------------------------------
# 회귀식 / 분석 조건
# --------------------------------------------------
st.subheader("회귀 분석 정보")

st.write(
    f"회귀식: **평균기온 = {intercept:.4f} + "
    f"{slope:.4f} × (연도 − 1908)**"
)

st.write(
    f"- 사용 연도: {year_count}개"
)
st.write(
    f"- 시작 연도: {start_year}년"
)
st.write(
    f"- 끝 연도: {end_year}년"
)
st.write(
    f"- 연도별 최소 관측일수: {MIN_DAYS}일"
)
st.write(
    f"- 기준 종료 연도: {LAST_YEAR}년"
)


# --------------------------------------------------
# 연도별 데이터 표
# --------------------------------------------------
with st.expander("회귀에 사용된 연도별 데이터 보기"):
    display_df = yearly.copy()
    display_df["평균기온"] = display_df["평균기온"].round(2)

    st.dataframe(
        display_df,
        use_container_width=True,
        hide_index=True,
    )
