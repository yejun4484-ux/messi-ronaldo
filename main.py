import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go

from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LinearRegression
from sklearn.metrics import r2_score, mean_absolute_error, mean_squared_error


# =========================================================
# 기본 설정
# =========================================================

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

MOVIES_URL = (
    "https://raw.githubusercontent.com/greatsong/modudata/main/data/"
    "kobis_movies.csv"
)

DAILY_URL = (
    "https://raw.githubusercontent.com/greatsong/modudata/main/data/"
    "kobis_daily.csv"
)


# =========================================================
# 데이터 불러오기
# =========================================================

@st.cache_data
def load_data():
    movies = pd.read_csv(MOVIES_URL, encoding="utf-8")
    daily = pd.read_csv(DAILY_URL, encoding="utf-8")

    return movies, daily


try:
    movies, daily = load_data()
except Exception as e:
    st.error(f"데이터를 불러오는 중 오류가 발생했습니다.\n\n{e}")
    st.stop()


# =========================================================
# 필요한 열 확인
# =========================================================

required_movies = [
    "movieCd",
    "movieNm",
    "openDt",
    "genre",
    "nation",
    "first_scrn",
    "first_show",
    "first_date",
    "peak",
    "first_week_audi",
    "total_audi",
    "days_in_top10"
]

required_daily = ["날짜", "영화코드"]

missing_movies = [
    col for col in required_movies
    if col not in movies.columns
]

missing_daily = [
    col for col in required_daily
    if col not in daily.columns
]

if missing_movies:
    st.error(f"영화 정보 표에 다음 열이 없습니다: {missing_movies}")
    st.stop()

if missing_daily:
    st.error(f"일별 박스오피스 표에 다음 열이 없습니다: {missing_daily}")
    st.stop()


# =========================================================
# 일별 데이터에서 기준 기간 계산
# =========================================================

daily["날짜_dt"] = pd.to_datetime(
    daily["날짜"].astype(str),
    format="%Y%m%d",
    errors="coerce"
)

start_date = daily["날짜_dt"].min()
end_date = daily["날짜_dt"].max()

if pd.isna(start_date) or pd.isna(end_date):
    period_text = "기간을 확인할 수 없습니다."
else:
    period_text = (
        f"{start_date.strftime('%Y-%m-%d')} ~ "
        f"{end_date.strftime('%Y-%m-%d')}"
    )


# =========================================================
# 영화 데이터 정리
# =========================================================

# 영화코드는 문자열로 처리
movies["movieCd"] = movies["movieCd"].astype(str)

# 영화코드 순으로 정렬
movies = movies.sort_values("movieCd").reset_index(drop=True)

# 영화명도 문자열
movies["movieNm"] = movies["movieNm"].astype(str)

# 장르가 여러 개라면 첫 번째 장르만 사용
movies["genre"] = (
    movies["genre"]
    .fillna("미상")
    .astype(str)
    .str.split("|")
    .str[0]
)

# 국가 데이터 정리
movies["nation"] = (
    movies["nation"]
    .fillna("미상")
    .astype(str)
)

# 숫자형 변수 변환
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

# 날짜 변수
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


# =========================================================
# 영화 데이터의 맨 위 행 표시
# =========================================================

st.subheader("📋 영화 정보 표의 맨 위 행")

# 화면에는 원래 열 이름과 값을 그대로 보여주기 위해
# 날짜도 다시 8자리 숫자로 표시
top_row = movies.head(1).copy()

top_row["openDt"] = top_row["openDt"].dt.strftime("%Y%m%d")
top_row["first_date"] = top_row["first_date"].dt.strftime("%Y%m%d")

st.dataframe(
    top_row,
    use_container_width=True,
    hide_index=True
)


# =========================================================
# 기본 정보
# =========================================================

st.subheader("📊 데이터 정보")

info1, info2, info3, info4 = st.columns(4)

info1.metric(
    "영화 수",
    f"{len(movies):,}편"
)

info2.metric(
    "학습 영화 수",
    f"{len(movies) - ((len(movies) + 9) // 10) * 3 if len(movies) >= 3 else 0:,}편"
)

# 테스트 영화 수 계산
test_indices = []

for i in range(0, len(movies), 10):
    test_indices.extend(
        list(range(i, min(i + 3, len(movies))))
    )

test_indices = sorted(set(test_indices))

test_count = len(test_indices)
train_count = len(movies) - test_count

info2.metric(
    "학습에 사용한 영화",
    f"{train_count:,}편"
)

info3.metric(
    "평가한 영화",
    f"{test_count:,}편"
)

info4.metric(
    "기준 기간",
    period_text
)


# =========================================================
# 변수 선택
# =========================================================

st.subheader("🎛️ 예측 변수 선택")

st.write(
    "체크한 변수만 다중 회귀 모델의 입력 변수로 사용합니다."
)

# 실제로 선택 가능한 변수
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
    "openDt": "개봉일(openDt)",
    "genre": "장르(genre)",
    "nation": "국가(nation)",
    "first_scrn": "첫 관측일 스크린수(first_scrn)",
    "first_show": "첫 관측일 상영횟수(first_show)",
    "first_date": "10위권 첫 등장일(first_date)",
    "peak": "성수기 개봉 여부(peak)",
    "first_week_audi": "첫 주 관객(first_week_audi)",
    "days_in_top10": "10위권 등장일수(days_in_top10)"
}

selected_features = []

checkbox_cols = st.columns(3)

for idx, feature in enumerate(feature_options):
    with checkbox_cols[idx % 3]:
        checked = st.checkbox(
            feature_labels[feature],
            value=True,
            key=f"feature_{feature}"
        )

        if checked:
            selected_features.append(feature)


if len(selected_features) == 0:
    st.warning("최소 1개의 예측 변수를 선택해 주세요.")
    st.stop()


# =========================================================
# 회귀용 데이터 만들기
# =========================================================

model_df = movies[selected_features + ["total_audi"]].copy()

# 날짜 → 숫자형 날짜
for col in ["openDt", "first_date"]:
    if col in model_df.columns:
        model_df[col] = model_df[col].map(
            lambda x: x.toordinal()
            if pd.notna(x)
            else np.nan
        )

# 문자열 컬럼
categorical_features = [
    col for col in selected_features
    if model_df[col].dtype == "object"
]

# 숫자형 컬럼
numeric_features = [
    col for col in selected_features
    if col not in categorical_features
]

# =========================================================
# 학습/테스트 분리
# =========================================================

# movieCd 순으로 정렬한 상태에서
# 10편마다 앞의 3편을 테스트용으로 사용
test_mask = np.zeros(len(movies), dtype=bool)

for i in range(0, len(movies), 10):
    test_mask[i:min(i + 3, len(movies))] = True

train_mask = ~test_mask

train_df = model_df.loc[train_mask].copy()
test_df = model_df.loc[test_mask].copy()

train_movies = movies.loc[train_mask].copy()
test_movies = movies.loc[test_mask].copy()

X_train = train_df[selected_features]
y_train = train_df["total_audi"]

X_test = test_df[selected_features]
y_test = test_df["total_audi"]


# =========================================================
# 전처리 + 다중 회귀 모델
# =========================================================

transformers = []

if numeric_features:
    numeric_pipeline = Pipeline(
        steps=[
            (
                "imputer",
                SimpleImputer(strategy="median")
            )
        ]
    )

    transformers.append(
        (
            "numeric",
            numeric_pipeline,
            numeric_features
        )
    )

if categorical_features:
    categorical_pipeline = Pipeline(
        steps=[
            (
                "imputer",
                SimpleImputer(
                    strategy="most_frequent"
                )
            ),
            (
                "onehot",
                OneHotEncoder(
                    handle_unknown="ignore"
                )
            )
        ]
    )

    transformers.append(
        (
            "categorical",
            categorical_pipeline,
            categorical_features
        )
    )


preprocessor = ColumnTransformer(
    transformers=transformers
)

model = Pipeline(
    steps=[
        ("preprocessor", preprocessor),
        ("regressor", LinearRegression())
    ]
)


# =========================================================
# 모델 학습
# =========================================================

try:
    model.fit(X_train, y_train)

    predictions = model.predict(X_test)

except Exception as e:
    st.error(
        "모델을 학습하는 중 오류가 발생했습니다.\n\n"
        f"{e}"
    )
    st.stop()


# =========================================================
# 예측값 후처리
# =========================================================

# 실제 평가에서는 모델의 원래 예측값 사용
predictions_raw = predictions.copy()

# 총 관객 수는 음수가 될 수 없으므로
# 표시용 값은 최소 1명으로 제한
predictions_display = np.maximum(
    predictions_raw,
    1
)


# =========================================================
# 평가 지표
# =========================================================

r2 = r2_score(
    y_test,
    predictions_raw
)

mae = mean_absolute_error(
    y_test,
    predictions_raw
)

rmse = np.sqrt(
    mean_squared_error(
        y_test,
        predictions_raw
    )
)

# 실제 관객 수가 0인 경우 발생할 수 있는 문제 방지
non_zero_mask = y_test != 0

if non_zero_mask.any():
    mape = np.mean(
        np.abs(
            (
                y_test[non_zero_mask].values
                - predictions_raw[non_zero_mask]
            )
            / y_test[non_zero_mask].values
        )
    ) * 100
else:
    mape = np.nan


# =========================================================
# 평가 결과
# =========================================================

st.subheader("📈 학습 및 평가 결과")

metric1, metric2, metric3, metric4 = st.columns(4)

metric1.metric(
    "R² 점수",
    f"{r2:.3f}"
)

metric2.metric(
    "평균 절대 오차(MAE)",
    f"{mae:,.0f}명"
)

metric3.metric(
    "RMSE",
    f"{rmse:,.0f}명"
)

if np.isnan(mape):
    metric4.metric(
        "평균 절대 오차율",
        "계산 불가"
    )
else:
    metric4.metric(
        "평균 절대 오차율",
        f"{mape:.1f}%"
    )

st.write(
    f"**학습에 사용한 영화:** {train_count:,}편  |  "
    f"**평가한 영화:** {test_count:,}편  |  "
    f"**기준 기간:** {period_text}"
)

st.caption(
    "테스트 영화는 모델 학습에 전혀 사용하지 않은 영화입니다."
)


# =========================================================
# 실제값 / 예측값 데이터프레임
# =========================================================

result_df = pd.DataFrame({
    "영화코드": test_movies["movieCd"].values,
    "영화명": test_movies["movieNm"].values,
    "실제 총 관객 수": y_test.values,
    "예측 총 관객 수": predictions_raw,
})

result_df["절대 오차"] = np.abs(
    result_df["실제 총 관객 수"]
    - result_df["예측 총 관객 수"]
)

result_df["오차율(%)"] = np.where(
    result_df["실제 총 관객 수"] != 0,
    result_df["절대 오차"]
    / result_df["실제 총 관객 수"]
    * 100,
    np.nan
)

result_df = result_df.sort_values(
    "영화코드"
).reset_index(drop=True)


# =========================================================
# 테스트 결과 표
# =========================================================

st.subheader("🎞️ 테스트 영화별 예측 결과")

display_result = result_df.copy()

display_result["실제 총 관객 수"] = (
    display_result["실제 총 관객 수"]
    .round()
    .astype(int)
)

display_result["예측 총 관객 수"] = (
    display_result["예측 총 관객 수"]
    .round()
    .astype(int)
)

display_result["절대 오차"] = (
    display_result["절대 오차"]
    .round()
    .astype(int)
)

display_result["오차율(%)"] = (
    display_result["오차율(%)"]
    .round(1)
)

st.dataframe(
    display_result,
    use_container_width=True,
    hide_index=True
)


# =========================================================
# 실제값 vs 예측값 산점도
# =========================================================

st.subheader("🎯 실제 총 관객 수 vs 예측 총 관객 수")

# 로그 축에서 사용할 실제/예측값
plot_actual = np.maximum(
    result_df["실제 총 관객 수"].astype(float).values,
    1
)

plot_predicted = np.maximum(
    predictions_display.astype(float),
    1
)

# 1,000명 미만 예측 영화
low_prediction_mask = predictions_raw < 1000

low_prediction_count = int(
    low_prediction_mask.sum()
)

# 그래프 범위
all_values = np.concatenate(
    [
        plot_actual,
        plot_predicted
    ]
)

min_value = max(
    1,
    np.min(all_values)
)

max_value = max(
    1000,
    np.max(all_values)
)

# 로그 범위에 약간의 여유
line_min = min_value
line_max = max_value

fig = go.Figure()


# ---------------------------------------------------------
# 실제값 vs 예측값
# ---------------------------------------------------------

normal_mask = ~low_prediction_mask

fig.add_trace(
    go.Scatter(
        x=plot_actual[normal_mask],
        y=plot_predicted[normal_mask],
        mode="markers",
        name="테스트 영화",
        text=result_df.loc[
            normal_mask,
            "영화명"
        ],
        customdata=result_df.loc[
            normal_mask,
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


# ---------------------------------------------------------
# 예측값 1,000명 미만 영화
# 그래프 바닥에 붙여 표시
# ---------------------------------------------------------

if low_prediction_count > 0:

    low_actual = plot_actual[low_prediction_mask]

    low_names = result_df.loc[
        low_prediction_mask,
        "영화명"
    ].values

    low_codes = result_df.loc[
        low_prediction_mask,
        "영화코드"
    ].values

    low_real = result_df.loc[
        low_prediction_mask,
        "실제 총 관객 수"
    ].values

    low_pred = result_df.loc[
        low_prediction_mask,
        "예측 총 관객 수"
    ].values

    low_error = result_df.loc[
        low_prediction_mask,
        "절대 오차"
    ].values

    low_error_rate = result_df.loc[
        low_prediction_mask,
        "오차율(%)"
    ].values

    # 그래프 바닥에 붙일 y값
    floor_y = np.full(
        len(low_actual),
        max(1, line_min)
    )

    fig.add_trace(
        go.Scatter(
            x=low_actual,
            y=floor_y,
            mode="markers",
            name="예측 1,000명 미만",
            text=low_names,
            customdata=np.column_stack(
                [
                    low_codes,
                    low_real,
                    low_pred,
                    low_error,
                    low_error_rate
                ]
            ),
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


# ---------------------------------------------------------
# 실제값 = 예측값 대각선
# ---------------------------------------------------------

fig.add_trace(
    go.Scatter(
        x=[line_min, line_max],
        y=[line_min, line_max],
        mode="lines",
        name="실제값 = 예측값",
        line=dict(
            dash="dash"
        ),
        hoverinfo="skip"
    )
)


# ---------------------------------------------------------
# 레이아웃
# ---------------------------------------------------------

fig.update_layout(
    xaxis_title="실제 총 관객 수",
    yaxis_title="예측한 총 관객 수",
    height=650,
    hovermode="closest",
    legend_title="구분"
)

fig.update_xaxes(
    type="log",
    range=[
        np.log10(line_min),
        np.log10(line_max)
    ]
)

fig.update_yaxes(
    type="log",
    range=[
        np.log10(line_min),
        np.log10(line_max)
    ]
)

st.plotly_chart(
    fig,
    use_container_width=True
)


# =========================================================
# 1,000명 미만 예측 결과
# =========================================================

st.info(
    f"예측 총 관객 수가 1,000명보다 작게 나온 영화는 "
    f"**{low_prediction_count}편**입니다."
)

if low_prediction_count > 0:

    low_result = result_df[
        low_prediction_mask
    ].copy()

    low_result["실제 총 관객 수"] = (
        low_result["실제 총 관객 수"]
        .round()
        .astype(int)
    )

    low_result["예측 총 관객 수"] = (
        low_result["예측 총 관객 수"]
        .round()
        .astype(int)
    )

    low_result["절대 오차"] = (
        low_result["절대 오차"]
        .round()
        .astype(int)
    )

    low_result["오차율(%)"] = (
        low_result["오차율(%)"]
        .round(1)
    )

    st.dataframe(
        low_result,
        use_container_width=True,
        hide_index=True
    )


# =========================================================
# 사용한 변수
# =========================================================

with st.expander("🔎 현재 모델에 사용된 변수 보기"):

    st.write(
        [
            feature_labels[f]
            for f in selected_features
        ]
    )

    st.write(
        f"총 {len(selected_features)}개의 변수를 선택했습니다."
    )

    st.caption(
        "genre와 nation은 범주형 변수이므로 원-핫 인코딩 후 "
        "회귀 모델에 입력됩니다."
    )
