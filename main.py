```python
import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go

from sklearn.linear_model import LinearRegression
from sklearn.metrics import r2_score, mean_absolute_error, mean_squared_error


# ============================================================
# 페이지 설정
# ============================================================

st.set_page_config(
    page_title="영화 흥행 예측기",
    page_icon="🎬",
    layout="wide"
)

st.title("🎬 영화 흥행 예측기")

st.write(
    "영화 정보 데이터를 이용해 영화의 총 관객 수를 "
    "다중 회귀 모델로 예측합니다."
)


# ============================================================
# 데이터 주소
# ============================================================

DAILY_URL = (
    "https://raw.githubusercontent.com/greatsong/modudata/main/data/"
    "kobis_daily.csv"
)

MOVIES_URL = (
    "https://raw.githubusercontent.com/greatsong/modudata/main/data/"
    "kobis_movies.csv"
)


# ============================================================
# 데이터 불러오기
# ============================================================

@st.cache_data
def load_data():

    daily = pd.read_csv(
        DAILY_URL,
        encoding="utf-8"
    )

    movies = pd.read_csv(
        MOVIES_URL,
        encoding="utf-8"
    )

    return daily, movies


try:
    daily, movies = load_data()

except Exception as e:

    st.error(
        "데이터를 불러오는 중 오류가 발생했습니다."
    )

    st.code(str(e))

    st.stop()


# ============================================================
# 기준 기간 계산
# ============================================================

daily["날짜_dt"] = pd.to_datetime(
    daily["날짜"].astype(str),
    format="%Y%m%d",
    errors="coerce"
)

start_date = daily["날짜_dt"].min()
end_date = daily["날짜_dt"].max()

if pd.notna(start_date) and pd.notna(end_date):

    period_text = (
        f"{start_date.strftime('%Y-%m-%d')} ~ "
        f"{end_date.strftime('%Y-%m-%d')}"
    )

else:

    period_text = "기간 확인 불가"


# ============================================================
# 영화 데이터 정리
# ============================================================

# 영화코드는 문자열
movies["movieCd"] = movies["movieCd"].astype(str)

# 영화코드 순으로 정렬
movies = (
    movies
    .sort_values("movieCd")
    .reset_index(drop=True)
)


# ============================================================
# 장르 / 국가 정리
# ============================================================

movies["genre"] = (
    movies["genre"]
    .fillna("미상")
    .astype(str)
    .str.split("|")
    .str[0]
)

movies["nation"] = (
    movies["nation"]
    .fillna("미상")
    .astype(str)
)


# ============================================================
# 숫자형 변수 변환
# ============================================================

numeric_columns = [
    "first_scrn",
    "first_show",
    "peak",
    "first_week_audi",
    "total_audi",
    "days_in_top10"
]

for col in numeric_columns:

    movies[col] = pd.to_numeric(
        movies[col],
        errors="coerce"
    )


# ============================================================
# 날짜 변환
# ============================================================

movies["openDt"] = pd.to_datetime(
    movies["openDt"].astype(str),
    format="%Y%m%d",
    errors="coerce"
)

movies["first_date"] = pd.to_datetime(
    movies["first_date"].astype(str),
    format="%Y%m%d",
    errors="coerce"
)


# ============================================================
# 영화 정보 표의 맨 위 행
# ============================================================

st.subheader("📋 영화 정보 표")

top_row = movies.head(1).copy()

# 화면 표시용으로 날짜를 다시 8자리 숫자로 변경
top_row["openDt"] = top_row["openDt"].dt.strftime("%Y%m%d")
top_row["first_date"] = top_row["first_date"].dt.strftime("%Y%m%d")

st.dataframe(
    top_row,
    use_container_width=True,
    hide_index=True
)


# ============================================================
# 기본 데이터 정보
# ============================================================

st.subheader("📊 데이터 및 평가 정보")


# 10편마다 앞 3편을 테스트용으로 사용
test_mask = np.zeros(
    len(movies),
    dtype=bool
)

for i in range(0, len(movies), 10):

    test_mask[
        i:min(i + 3, len(movies))
    ] = True


train_mask = ~test_mask

train_count = int(train_mask.sum())
test_count = int(test_mask.sum())


info1, info2, info3, info4 = st.columns(4)

info1.metric(
    "전체 영화",
    f"{len(movies):,}편"
)

info2.metric(
    "학습 영화",
    f"{train_count:,}편"
)

info3.metric(
    "평가 영화",
    f"{test_count:,}편"
)

info4.metric(
    "기준 기간",
    period_text
)


# ============================================================
# 변수 선택
# ============================================================

st.subheader("🎛️ 예측 변수 선택")

st.write(
    "체크한 변수만 다중 회귀 모델의 입력값으로 사용합니다."
)


feature_options = [
    "openDt",
    "genre",
    "nation",
    "first_scrn",
    "first_show",
    "first_date",
    "peak",
    "first_week_audi",
    "days_in_top10"
]

feature_labels = {

    "openDt":
        "개봉일 (openDt)",

    "genre":
        "장르 (genre)",

    "nation":
        "국가 (nation)",

    "first_scrn":
        "첫 관측일 스크린수 (first_scrn)",

    "first_show":
        "첫 관측일 상영횟수 (first_show)",

    "first_date":
        "10위권 첫 등장일 (first_date)",

    "peak":
        "성수기 개봉 여부 (peak)",

    "first_week_audi":
        "첫 주 관객 (first_week_audi)",

    "days_in_top10":
        "10위권 등장일수 (days_in_top10)"
}


selected_features = []

cols = st.columns(3)

for i, feature in enumerate(feature_options):

    with cols[i % 3]:

        checked = st.checkbox(
            feature_labels[feature],
            value=True,
            key=f"check_{feature}"
        )

        if checked:

            selected_features.append(feature)


if len(selected_features) == 0:

    st.warning(
        "예측에 사용할 변수를 하나 이상 선택해 주세요."
    )

    st.stop()


# ============================================================
# 모델용 데이터 만들기
# ============================================================

model_df = movies[
    selected_features + ["total_audi"]
].copy()


# ============================================================
# 날짜를 숫자로 변경
# ============================================================

for col in ["openDt", "first_date"]:

    if col in model_df.columns:

        model_df[col] = model_df[col].apply(
            lambda x:
            x.toordinal()
            if pd.notna(x)
            else np.nan
        )


# ============================================================
# 범주형 변수 → 원-핫 인코딩
# ============================================================

categorical_columns = []

for col in selected_features:

    if model_df[col].dtype == "object":

        categorical_columns.append(col)


if categorical_columns:

    model_df = pd.get_dummies(
        model_df,
        columns=categorical_columns,
        dummy_na=True
    )


# ============================================================
# 모든 열 숫자로 변환
# ============================================================

for col in model_df.columns:

    model_df[col] = pd.to_numeric(
        model_df[col],
        errors="coerce"
    )


# ============================================================
# 결측값 처리
# ============================================================

for col in model_df.columns:

    if col == "total_audi":
        continue

    median_value = model_df[col].median()

    if pd.isna(median_value):
        median_value = 0

    model_df[col] = (
        model_df[col]
        .fillna(median_value)
    )


# ============================================================
# 목표 변수 결측 영화 제거
# ============================================================

valid_target = model_df["total_audi"].notna()

model_df = model_df.loc[
    valid_target
].reset_index(drop=True)

movies_for_model = movies.loc[
    valid_target
].reset_index(drop=True)

test_mask_model = test_mask[
    valid_target.values
]

train_mask_model = ~test_mask_model


# ============================================================
# X / y
# ============================================================

X = model_df.drop(
    columns=["total_audi"]
)

y = model_df["total_audi"]


X_train = X.loc[
    train_mask_model
]

X_test = X.loc[
    test_mask_model
]

y_train = y.loc[
    train_mask_model
]

y_test = y.loc[
    test_mask_model
]


# ============================================================
# 다중 회귀 모델
# ============================================================

model = LinearRegression()


try:

    model.fit(
        X_train,
        y_train
    )

    predictions = model.predict(
        X_test
    )

except Exception as e:

    st.error(
        "회귀 모델 학습 중 오류가 발생했습니다."
    )

    st.code(str(e))

    st.stop()


# ============================================================
# 평가 지표
# ============================================================

r2 = r2_score(
    y_test,
    predictions
)

mae = mean_absolute_error(
    y_test,
    predictions
)

rmse = np.sqrt(
    mean_squared_error(
        y_test,
        predictions
    )
)


# 평균 절대 오차율
non_zero = y_test != 0

if non_zero.any():

    mape = (
        np.mean(
            np.abs(
                (
                    y_test[non_zero].values
                    -
                    predictions[non_zero]
                )
                /
                y_test[non_zero].values
            )
        )
        * 100
    )

else:

    mape = np.nan


# ============================================================
# 평가 결과
# ============================================================

st.subheader("📈 모델 평가 점수")

m1, m2, m3, m4 = st.columns(4)

m1.metric(
    "R² 점수",
    f"{r2:.3f}"
)

m2.metric(
    "평균 절대 오차",
    f"{mae:,.0f}명"
)

m3.metric(
    "RMSE",
    f"{rmse:,.0f}명"
)

if np.isnan(mape):

    m4.metric(
        "평균 절대 오차율",
        "계산 불가"
    )

else:

    m4.metric(
        "평균 절대 오차율",
        f"{mape:.1f}%"
    )


st.write(
    f"**학습에 사용한 영화:** {len(X_train):,}편"
)

st.write(
    f"**점수를 평가한 영화:** {len(X_test):,}편"
)

st.write(
    f"**기준 기간:** {period_text}"
)


# ============================================================
# 테스트 영화 결과 표
# ============================================================

result_df = pd.DataFrame({

    "영화코드":
        movies_for_model.loc[
            test_mask_model,
            "movieCd"
        ].values,

    "영화명":
        movies_for_model.loc[
            test_mask_model,
            "movieNm"
        ].values,

    "실제 총 관객 수":
        y_test.values,

    "예측 총 관객 수":
        predictions

})


# 영화코드 순
result_df = (
    result_df
    .sort_values("영화코드")
    .reset_index(drop=True)
)


# 오차
result_df["절대 오차"] = np.abs(
    result_df["실제 총 관객 수"]
    -
    result_df["예측 총 관객 수"]
)


result_df["오차율(%)"] = np.where(

    result_df["실제 총 관객 수"] != 0,

    result_df["절대 오차"]
    /
    result_df["실제 총 관객 수"]
    * 100,

    np.nan
)


# ============================================================
# 테스트 영화 표
# ============================================================

st.subheader("🎞️ 테스트 영화 예측 결과")

display_df = result_df.copy()

for col in [
    "실제 총 관객 수",
    "예측 총 관객 수",
    "절대 오차"
]:

    display_df[col] = (
        display_df[col]
        .round()
        .astype(int)
    )


display_df["오차율(%)"] = (
    display_df["오차율(%)"]
    .round(1)
)


st.dataframe(
    display_df,
    use_container_width=True,
    hide_index=True
)


# ============================================================
# 산점도
# ============================================================

st.subheader(
    "🎯 실제 총 관객 수와 예측한 총 관객 수"
)


actual = np.maximum(
    result_df["실제 총 관객 수"].astype(float).values,
    1
)

predicted = np.maximum(
    result_df["예측 총 관객 수"].astype(float).values,
    1
)


# 예측값 1,000명 미만
low_mask = (
    result_df["예측 총 관객 수"]
    < 1000
)

low_count = int(
    low_mask.sum()
)


# 전체 그래프 범위
all_values = np.concatenate(
    [
        actual,
        predicted
    ]
)

graph_min = max(
    1,
    float(np.min(all_values))
)

graph_max = max(
    1000,
    float(np.max(all_values))
)


fig = go.Figure()


# ============================================================
# 일반 예측 영화
# ============================================================

normal_mask = ~low_mask.values


if normal_mask.any():

    normal_result = result_df.loc[
        normal_mask
    ]

    fig.add_trace(
        go.Scatter(

            x=actual[normal_mask],

            y=predicted[normal_mask],

            mode="markers",

            name="테스트 영화",

            text=normal_result["영화명"],

            customdata=normal_result[
                [
                    "영화코드",
                    "실제 총 관객 수",
                    "예측 총 관객 수",
                    "절대 오차",
                    "오차율(%)"
                ]
            ],

            hovertemplate=(
                "<b>%{text}</b><br>"
                "영화코드: %{customdata[0]}<br>"
                "실제 관객: %{customdata[1]:,.0f}명<br>"
                "예측 관객: %{customdata[2]:,.0f}명<br>"
                "절대 오차: %{customdata[3]:,.0f}명<br>"
                "오차율: %{customdata[4]:.1f}%"
                "<extra></extra>"
            ),

            marker=dict(
                size=9
            )
        )
    )


# ============================================================
# 1,000명 미만 예측 영화
# ============================================================

if low_count > 0:

    low_result = result_df.loc[
        low_mask
    ]

    low_actual = np.maximum(
        low_result["실제 총 관객 수"].values,
        1
    )

    # 그래프 바닥
    floor_y = np.full(
        len(low_result),
        graph_min
    )

    fig.add_trace(
        go.Scatter(

            x=low_actual,

            y=floor_y,

            mode="markers",

            name="예측 1,000명 미만",

            text=low_result["영화명"],

            customdata=low_result[
                [
                    "영화코드",
                    "실제 총 관객 수",
                    "예측 총 관객 수",
                    "절대 오차",
                    "오차율(%)"
                ]
            ],

            hovertemplate=(
                "<b>%{text}</b><br>"
                "영화코드: %{customdata[0]}<br>"
                "실제 관객: %{customdata[1]:,.0f}명<br>"
                "예측 관객: %{customdata[2]:,.0f}명<br>"
                "절대 오차: %{customdata[3]:,.0f}명<br>"
                "오차율: %{customdata[4]:.1f}%"
                "<extra></extra>"
            ),

            marker=dict(
                size=11,
                symbol="diamond"
            )
        )
    )


# ============================================================
# 실제값 = 예측값 대각선
# ============================================================

fig.add_trace(
    go.Scatter(

        x=[
            graph_min,
            graph_max
        ],

        y=[
            graph_min,
            graph_max
        ],

        mode="lines",

        name="실제값 = 예측값",

        line=dict(
            dash="dash"
        ),

        hoverinfo="skip"
    )
)


# ============================================================
# 로그 축
# ============================================================

fig.update_xaxes(
    type="log",
    title="실제 총 관객 수"
)

fig.update_yaxes(
    type="log",
    title="예측한 총 관객 수"
)


fig.update_layout(
    height=650,
    hovermode="closest",
    legend_title="구분"
)


st.plotly_chart(
    fig,
    use_container_width=True
)


# ============================================================
# 1,000명 미만 결과
# ============================================================

st.info(
    f"예측한 총 관객 수가 1,000명보다 작은 영화는 "
    f"**{low_count}편**입니다."
)


if low_count > 0:

    st.write(
        "아래 영화들은 산점도에서 그래프 바닥에 붙여 표시했습니다."
    )

    low_display = result_df.loc[
        low_mask
    ].copy()

    low_display["실제 총 관객 수"] = (
        low_display["실제 총 관객 수"]
        .round()
        .astype(int)
    )

    low_display["예측 총 관객 수"] = (
        low_display["예측 총 관객 수"]
        .round()
        .astype(int)
    )

    low_display["절대 오차"] = (
        low_display["절대 오차"]
        .round()
        .astype(int)
    )

    low_display["오차율(%)"] = (
        low_display["오차율(%)"]
        .round(1)
    )

    st.dataframe(
        low_display,
        use_container_width=True,
        hide_index=True
    )


# ============================================================
# 선택한 변수 표시
# ============================================================

st.subheader("🔎 현재 모델에 사용한 변수")

for feature in selected_features:

    st.write(
        f"✓ {feature_labels[feature]}"
    )


st.caption(
    "장르와 국가는 여러 범주를 숫자로 변환하기 위해 "
    "원-핫 인코딩 방식으로 처리했습니다."
)
```
