python
import streamlit as st
import pandas as pd
import plotly.express as px


# -----------------------------------
# 페이지 설정
# -----------------------------------
st.set_page_config(
    page_title="영화 데이터 그래프 도감 2 - 분포와 관계",
    page_icon="🎬",
    layout="wide"
)

st.title("🎬 영화 데이터 그래프 도감 2 - 분포와 관계")
st.markdown(
    "1년간 박스오피스 10위권에 든 영화 가운데 "
    "이 기간에 개봉한 216편의 데이터를 살펴봅니다."
)


# -----------------------------------
# 데이터 불러오기
# -----------------------------------
DATA_URL = (
    "https://raw.githubusercontent.com/greatsong/modudata/"
    "main/data/kobis_movies.csv"
)


@st.cache_data
def load_data():
    df = pd.read_csv(DATA_URL)

    # 개봉일: 여덟 자리 숫자 → 날짜 형식으로 변환
    df["openDt"] = pd.to_datetime(
        df["openDt"].astype(str),
        format="%Y%m%d",
        errors="coerce"
    )

    # genre에 여러 장르가 "|"로 연결되어 있으면 첫 번째 장르만 사용
    df["genre"] = (
        df["genre"]
        .fillna("미상")
        .astype(str)
        .str.split("|")
        .str[0]
        .str.strip()
    )

    # 빈 장르는 미상으로 처리
    df.loc[df["genre"] == "", "genre"] = "미상"

    return df


df = load_data()


# -----------------------------------
# 데이터 개요
# -----------------------------------
st.subheader("📊 데이터 개요")

col1, col2, col3 = st.columns(3)

with col1:
    st.metric("영화 수", f"{len(df):,}편")

with col2:
    st.metric("장르 수", f"{df['genre'].nunique():,}개")

with col3:
    st.metric("데이터 열 수", f"{len(df.columns):,}개")


st.divider()


# ===================================
# 그래프 1. 장르별 영화 편수
# ===================================
st.subheader("1. 장르별 영화 편수")

genre_count = (
    df["genre"]
    .value_counts()
    .reset_index()
)

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

st.plotly_chart(fig1, use_container_width=True)

st.markdown(
    """
    <div style="
        border-left: 4px solid #4A90E2;
        padding: 12px 16px;
        margin-top: 8px;
        margin-bottom: 30px;
        background-color: rgba(74, 144, 226, 0.08);
        border-radius: 4px;
    ">
        <b>이 그래프로 알 수 있는 것</b><br>
        어떤 장르의 영화가 이 기간에 개봉한 박스오피스 10위권 영화에서
        많이 차지했는지 한눈에 비교할 수 있습니다.
    </div>
    """,
    unsafe_allow_html=True
)


# ===================================
# 그래프 2. 장르별 영화 트리맵
# ===================================
st.subheader("2. 장르별 영화 관객수 트리맵")

# 총 관객수를 숫자로 변환
df_treemap = df.copy()

df_treemap["total_audi"] = pd.to_numeric(
    df_treemap["total_audi"],
    errors="coerce"
)

# 총 관객수가 없는 행 제거
df_treemap = df_treemap.dropna(
    subset=["total_audi"]
)

# 트리맵
fig2 = px.treemap(
    df_treemap,
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

st.plotly_chart(fig2, use_container_width=True)

st.markdown(
    """
    <div style="
        border-left: 4px solid #4A90E2;
        padding: 12px 16px;
        margin-top: 8px;
        margin-bottom: 30px;
        background-color: rgba(74, 144, 226, 0.08);
        border-radius: 4px;
    ">
        <b>이 그래프로 알 수 있는 것</b><br>
        각 장르 안에서 어떤 영화가 많은 관객을 모았는지와
        영화별 관객 규모의 차이를 면적을 통해 비교할 수 있습니다.
    </div>
    """,
    unsafe_allow_html=True
)


# -----------------------------------
# 원본 데이터 미리 보기
# -----------------------------------
with st.expander("원본 데이터 미리 보기"):
    st.dataframe(df, use_container_width=True)
```
