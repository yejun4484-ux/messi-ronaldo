
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
bins = pd.cut(
    hist_data["total_audi"],
    bins=20,
    include_lowest=True
)

bin_counts = bins.value_counts().sort_index()
most_common_bin = bin_counts.idxmax()

lower_bound = most_common_bin.left
upper_bound = most_common_bin.right


# 가장 관객이 많은 영화
top_movie = hist_data.loc[
    hist_data["total_audi"].idxmax()
]

top_movie_name = top_movie["movieNm"]
top_movie_audi = int(top_movie["total_audi"])

st.info(
    f"이 그래프로 알 수 있는 것: "
    f"대부분의 영화는 총 관객수 "
    f"{lower_bound:,.0f}명 ~ {upper_bound:,.0f}명 구간에 몰려 있으며, "
    f"가장 관객이 많은 영화는 "
    f"{top_movie_name}({top_movie_audi:,.0f}명)입니다."
)


# ==========================================
# 그래프 4. 개봉일 스크린수와 총 관객의 관계
# ==========================================

st.subheader("4. 개봉일 스크린수와 총 관객의 관계")

scatter_data = df.dropna(
    subset=["first_scrn", "total_audi", "movieNm", "genre"]
).copy()

fig4 = px.scatter(
    scatter_data,
    x="first_scrn",
    y="total_audi",
    color="genre",
    hover_name="movieNm",
    hover_data={
        "first_scrn": ":,.0f",
        "total_audi": ":,.0f",
        "genre": True
    },
    labels={
        "first_scrn": "개봉일 스크린수",
        "total_audi": "총 관객수",
        "genre": "장르"
    },
    title="개봉일 스크린수와 총 관객수"
)

fig4.update_traces(
    marker=dict(
        size=9,
        opacity=0.75
    ),
    hovertemplate=(
        "<b>%{hovertext}</b><br>"
        "장르: %{customdata[2]}<br>"
        "개봉일 스크린수: %{x:,.0f}개<br>"
        "총 관객수: %{y:,.0f}명"
        "<extra></extra>"
    )
)

fig4.update_layout(
    xaxis_title="개봉일 스크린수",
    yaxis_title="총 관객수",
    margin=dict(t=60, l=20, r=20, b=20)
)

st.plotly_chart(
    fig4,
    use_container_width=True
)

st.info(
    "이 그래프로 알 수 있는 것: "
    "개봉일에 더 많은 스크린을 확보한 영화가 총 관객수에서도 "
    "더 높은 성과를 보이는지 영화별로 비교할 수 있습니다."
)


# ==========================================
# 원본 데이터
# ==========================================

with st.expander("원본 데이터 미리 보기"):
    st.dataframe(
        df,
        use_container_width=True
    )

