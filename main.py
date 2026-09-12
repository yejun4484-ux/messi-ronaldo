
import streamlit as st
import pandas as pd
import plotly.express as px

st.set_page_config(
    page_title="영화 데이터 그래프 도감 2 - 분포와 관계",
    page_icon="🎬",
    layout="wide"
)

st.title("🎬 영화 데이터 그래프 도감 2 - 분포와 관계")
st.write(
    "1년간 박스오피스 10위권에 든 영화 가운데 "
    "이 기간에 개봉한 216편의 데이터를 살펴봅니다."
)

DATA_URL = "https://raw.githubusercontent.com/greatsong/modudata/main/data/kobis_movies.csv"


@st.cache_data
def load_data():
    df = pd.read_csv(DATA_URL)

    # 개봉일
    df["openDt"] = pd.to_datetime(
        df["openDt"].astype(str),
        format="%Y%m%d",
        errors="coerce"
    )

    # 여러 장르가 있으면 첫 번째 장르만 사용
    df["genre"] = (
        df["genre"]
        .fillna("미상")
        .astype(str)
        .str.split("|")
        .str[0]
        .str.strip()
    )

    df.loc[df["genre"] == "", "genre"] = "미상"

    # 숫자형 데이터 변환
    df["total_audi"] = pd.to_numeric(
        df["total_audi"],
        errors="coerce"
    )

    df["first_scrn"] = pd.to_numeric(
        df["first_scrn"],
        errors="coerce"
    )

    return df


df = load_data()


# ==========================================
# 데이터 개요
# ==========================================

st.subheader("📊 데이터 개요")

col1, col2, col3 = st.columns(3)

with col1:
    st.metric("영화 수", f"{len(df):,}편")

with col2:
    st.metric("장르 수", f"{df['genre'].nunique():,}개")

with col3:
    st.metric("데이터 열 수", f"{len(df.columns):,}개")

st.divider()


# ==========================================
# 그래프 1. 장르별 영화 편수
# ==========================================

st.subheader("1. 장르별 영화 편수")

genre_count = df["genre"].value_counts().reset_index()
genre_count.columns = ["장르", "영화 편수"]

fig1 = px.pie(
    genre_count,
    names="장르",
    values="영화 편수",
    hole=0.55,
    title="장르별 영화 편수"
)

fig1.update_traces(
    textinfo="percent",
    hovertemplate=(
        "<b>%{label}</b><br>"
        "영화 편수: %{value}편<br>"
        "비율: %{percent}<extra></extra>"
    )
)

fig1.update_layout(
    legend_title_text="장르",
    margin=dict(t=60, l=20, r=20, b=20)
)

st.plotly_chart(
    fig1,
    use_container_width=True
)

st.info(
    "이 그래프로 알 수 있는 것: "
    "어떤 장르의 영화가 이 기간에 개봉한 박스오피스 10위권 영화에서 "
    "많이 차지했는지 한눈에 비교할 수 있습니다."
)


# ==========================================
# 그래프 2. 장르별 영화 관객수 트리맵
# ==========================================

st.subheader("2. 장르별 영화 관객수 트리맵")

treemap_data = df.dropna(
    subset=["total_audi", "movieNm", "genre"]
).copy()

fig2 = px.treemap(
    treemap_data,
    path=["genre", "movieNm"],
    values="total_audi",
    title="장르 안에 들어 있는 영화별 총 관객수"
)

fig2.update_traces(
    hovertemplate=(
        "<b>%{label}</b><br>"
        "총 관객: %{value:,.0f}명"
        "<extra></extra>"
    )
)

fig2.update_layout(
    margin=dict(t=60, l=10, r=10, b=10)
)

st.plotly_chart(
    fig2,
    use_container_width=True
)

st.info(
    "이 그래프로 알 수 있는 것: "
    "각 장르 안에서 어떤 영화가 많은 관객을 모았는지와 "
    "영화별 관객 규모의 차이를 면적을 통해 비교할 수 있습니다."
)


# ==========================================
# 그래프 3. 총 관객수 히스토그램
# ==========================================

st.subheader("3. 영화별 총 관객수 분포")

hist_data = df.dropna(
    subset=["total_audi", "movieNm"]
).copy()

fig3 = px.histogram(
    hist_data,
    x="total_audi",
    nbins=20,
    title="영화별 총 관객수 분포",
    labels={
        "total_audi": "총 관객수",
        "count": "영화 편수"
    }
)

fig3.update_layout(
    xaxis_title="총 관객수",
    yaxis_title="영화 편수",
    margin=dict(t=60, l=20, r=20, b=20)
)

st.plotly_chart(
    fig3,
    use_container_width=True
)


# 가장 많은 영화가 몰려 있는 구간
