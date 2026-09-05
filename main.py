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

import pandas as pd
import plotly.express as px
import streamlit as st

# 페이지 설정
st.set_page_config(
    page_title="서울 기온 분포 분석",
    page_icon="🌡️",
    layout="wide",
)

DATA_URL = (
    "https://raw.githubusercontent.com/greatsong/modudata/main/data/seoul.csv"
)


@st.cache_data
def load_data():
    df = pd.read_csv(DATA_URL)
    df.columns = df.columns.str.strip()

    # 날짜 컬럼 변환
    df["날짜"] = pd.to_datetime(df["날짜"])
    df["연도"] = df["날짜"].dt.year

    # 평균기온 컬럼 자동 탐색
    temp_col = [col for col in df.columns if "평균기온" in col][0]
    df_clean = df.dropna(subset=[temp_col]).copy()
    df_clean.rename(columns={temp_col: "평균기온"}, inplace=True)

    return df_clean


st.title("📊 서울 일별 평균기온 구간별 분포 (히스토그램)")
st.markdown(
    "지난 100여 년 동안 서울의 **일별 평균기온**이 어느 기온 구간에 가장 많이 분포되어 있는지 확인합니다."
)

try:
    df = load_data()

    # 사이드바 컨트롤
    st.sidebar.header("⚙️ 시각화 설정")
    bin_size = st.sidebar.slider(
        "기온 구간 간격 (℃)",
        min_value=1,
        max_value=5,
        value=2,
        step=1,
        help="히스토그램의 구간(Bin) 크기를 설정합니다.",
    )

    # 주요 일별 요약 통계량
    mean_temp = df["평균기온"].mean()
    median_temp = df["평균기온"].median()
    min_temp = df["평균기온"].min()
    max_temp = df["평균기온"].max()

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("총 관측 일수", f"{len(df):,} 일")
    col2.metric("전체 일평균 기온", f"{mean_temp:.1f} ℃")
    col3.metric("최저 일평균 기온", f"{min_temp:.1f} ℃")
    col4.metric("최고 일평균 기온", f"{max_temp:.1f} ℃")

    st.divider()

    # Plotly 히스토그램 생성
    fig = px.histogram(
        df,
        x="평균기온",
        nbins=int((max_temp - min_temp) / bin_size),
        title=f"서울 일별 평균기온 분포 (구간 간격: {bin_size}℃)",
        labels={"평균기온": "일별 평균기온 (℃)", "count": "일수 (Count)"},
        color_discrete_sequence=["#2980B9"],
    )

    # 평균값 및 중앙값 표시 선 추가
    fig.add_vline(
        x=mean_temp,
        line_dash="dash",
        line_color="red",
        annotation_text=f"평균 ({mean_temp:.1f}℃)",
        annotation_position="top right",
    )

    fig.add_vline(
        x=median_temp,
        line_dash="dot",
        line_color="green",
        annotation_text=f"중앙값 ({median_temp:.1f}℃)",
        annotation_position="top left",
    )

    fig.update_layout(
        bargap=0.05,
        xaxis=dict(showgrid=True, gridcolor="#EAEAEA"),
        yaxis=dict(showgrid=True, gridcolor="#EAEAEA", title="해당 구간 일수"),
        height=520,
        hovermode="x unified",
    )

    fig.update_traces(hovertemplate="기온 구간: %{x}℃<br>관측 일수: %{y:,}일")

    st.plotly_chart(fig, use_container_width=True)

    # 계절별/구간별 세부 데이터
    with st.expander("📌 기온 구간별 상세 일수 보기"):
        counts, bins = pd.cut(
            df["평균기온"],
            bins=range(
                int(min_temp) - 1, int(max_temp) + bin_size + 1, bin_size
            ),
            retbins=True,
        )
        dist_df = (
            df.groupby(counts, observed=False)
            .size()
            .reset_index(name="일수")
        )
        dist_df.columns = ["기온 구간 (℃)", "관측 일수"]
        dist_df["비율 (%)"] = (
            dist_df["관측 일수"] / len(df) * 100
        ).round(2)
        st.dataframe(dist_df, use_container_width=True)

except Exception as e:
    st.error(f"데이터 처리 중 오류가 발생했습니다: {e}")
import numpy as np
import pandas as pd
import plotly.express as px
import streamlit as st

# 페이지 기본 설정
st.set_page_config(
    page_title="서울 최저기온 vs 최고기온 관계 분석",
    page_icon="🌡️",
    layout="wide",
)

DATA_URL = (
    "https://raw.githubusercontent.com/greatsong/modudata/main/data/seoul.csv"
)


@st.cache_data
def load_data():
    df = pd.read_csv(DATA_URL)
    df.columns = df.columns.str.strip()

    # 날짜 데이터 변환
    df["날짜"] = pd.to_datetime(df["날짜"])
    df["연도"] = df["날짜"].dt.year
    df["월"] = df["날짜"].dt.month

    # 컬럼명 자동 탐색
    min_col = [col for col in df.columns if "최저기온" in col][0]
    max_col = [col for col in df.columns if "최고기온" in col][0]

    # 결측치 제거 및 컬럼 정제
    df_clean = df.dropna(subset=[min_col, max_col]).copy()
    df_clean.rename(
        columns={min_col: "최저기온", max_col: "최고기온"}, inplace=True
    )

    # 일교차 계산
    df_clean["일교차"] = df_clean["최고기온"] - df_clean["최저기온"]

    return df_clean


st.title("🌡️ 서울 최저기온 vs 최고기온 관계 분석 (산점도)")
st.markdown(
    "지난 100여 년간의 서울 일별 **최저기온**과 **최고기온** 간의 상관관계를 산점도로 분석합니다."
)

try:
    df = load_data()

    # 사이드바 설정 (월별 필터)
    st.sidebar.header("⚙️ 데이터 필터링")

    selected_months = st.sidebar.multiselect(
        "조회할 월 선택",
        options=list(range(1, 13)),
        default=list(range(1, 13)),
        format_func=lambda x: f"{x}월",
    )

    # 샘플링 옵션 (데이터 양이 많아 렌더링 속도 최적화용)
    sample_size = st.sidebar.select_slider(
        "표시할 데이터 수 (샘플링)",
        options=[5000, 10000, 20000, "전체 (약 4만건)"],
        value=10000,
    )

    # 데이터 필터링
    filtered_df = df[df["월"].isin(selected_months)]

    if sample_size != "전체 (약 4만건)" and len(filtered_df) > sample_size:
        display_df = filtered_df.sample(n=sample_size, random_state=42)
    else:
        display_df = filtered_df

    # 주요 상관관계 통계 수치
    corr = filtered_df["최저기온"].corr(filtered_df["최고기온"])
    avg_diurnal = filtered_df["일교차"].mean()
    max_diurnal = filtered_df["일교차"].max()

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("분석 대상 일수", f"{len(filtered_df):,} 일")
    col2.metric("상관계수 (r)", f"{corr:.3f}")
    col3.metric("평균 일교차", f"{avg_diurnal:.1f} ℃")
    col4.metric("최대 일교차", f"{max_diurnal:.1f} ℃")

    st.divider()

    # Plotly 산점도 생성
    fig = px.scatter(
        display_df,
        x="최저기온",
        y="최고기온",
        color="일교차",
        color_continuous_scale="Turbo",
        hover_data=["날짜"],
        title=f"서울 일별 최저기온 vs 최고기온 (표시된 데이터: {len(display_df):,}건)",
        labels={
            "최저기온": "최저기온 (℃)",
            "최고기온": "최고기온 (℃)",
            "일교차": "일교차(℃)",
        },
        opacity=0.6,
    )

    # y = x 대각 기준선 추가
    min_val = min(display_df["최저기온"].min(), display_df["최고기온"].min())
    max_val = max(display_df["최저기온"].max(), display_df["최고기온"].max())

    fig.add_shape(
        type="line",
        x0=min_val,
        y0=min_val,
        x1=max_val,
        y1=max_val,
        line=dict(color="Gray", width=1.5, dash="dash"),
    )

    fig.update_layout(
        xaxis=dict(showgrid=True, gridcolor="#EAEAEA"),
        yaxis=dict(showgrid=True, gridcolor="#EAEAEA"),
        height=600,
    )

    st.plotly_chart(fig, use_container_width=True)

    # 일교차 관련 인사이트 요약
    with st.expander("📌 데이터 인사이트 및 요약"):
        max_diurnal_row = filtered_df.loc[filtered_df["일교차"].idxmax()]
        st.write(
            f"- **상관계수({corr:.3f})**: 최저기온과 최고기온은 **매우 강한 양의 상관관계**를 보입니다."
        )
        st.write(
            f"- **역대 최대 일교차**: **{max_diurnal_row['날짜'].strftime('%Y-%m-%d')}** (최저 {max_diurnal_row['최저기온']}℃ / 최고 {max_diurnal_row['최고기온']}℃ / 일교차 **{max_diurnal_row['일교차']:.1f}℃**)"
        )
        st.write(
            "- 회색 점선($y=x$)에서 위로 멀어질수록 그날의 일교차가 컸음을 의미합니다."
        )

except Exception as e:
    st.error(f"데이터 처리 중 오류가 발생했습니다: {e}")
