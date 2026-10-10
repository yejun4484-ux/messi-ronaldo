
import streamlit as st
import pandas as pd
import plotly.express as px

# 페이지 설정
st.set_page_config(
    page_title="탐색 | 뇌졸중 예측 실습실",
    page_icon="🧭",
    layout="wide",
)

DATA_URL = (
    "https://raw.githubusercontent.com/"
    "greatsong/modudata/main/data/stroke.csv"
)


@st.cache_data
def load_data():
    return pd.read_csv(DATA_URL, encoding="utf-8")


st.title("🧭 데이터 탐색")
st.write(
    "나이, 평균 혈당, 건강 상태, BMI의 빈 값, "
    "흡연 상태를 살펴보며 데이터의 특징을 탐색합니다."
)

try:
    df = load_data()
except Exception as e:
    st.error(
        "데이터를 불러오지 못했습니다. "
        "인터넷 연결과 데이터 주소를 확인해 주세요."
    )
    st.code(str(e))
    st.stop()

# 필요한 열을 숫자로 변환
for col in [
    "age",
    "avg_glucose_level",
    "bmi",
    "hypertension",
    "heart_disease",
    "stroke",
]:
    df[col] = pd.to_numeric(df[col], errors="coerce")


# ==================================================
# 1. 나이와 평균 혈당 분포
# ==================================================
st.markdown("## 1. 나이와 평균 혈당의 분포")

left, right = st.columns(2)

with left:
    age_data = df.dropna(subset=["age"])

    fig_age = px.histogram(
        age_data,
        x="age",
        nbins=30,
        title="나이 분포",
        labels={
            "age": "나이",
            "count": "사람 수",
        },
    )

    fig_age.update_layout(
        xaxis_title="나이",
        yaxis_title="사람 수",
        bargap=0.08,
    )

    st.plotly_chart(
        fig_age,
        use_container_width=True,
    )

with right:
    glucose_data = df.dropna(
        subset=["avg_glucose_level"]
    )

    fig_glucose = px.histogram(
        glucose_data,
        x="avg_glucose_level",
        nbins=30,
        title="평균 혈당 분포",
        labels={
            "avg_glucose_level": "평균 혈당",
            "count": "사람 수",
        },
    )

    fig_glucose.update_layout(
        xaxis_title="평균 혈당",
        yaxis_title="사람 수",
        bargap=0.08,
    )

    st.plotly_chart(
        fig_glucose,
        use_container_width=True,
    )

st.caption(
    "히스토그램은 값이 어느 구간에 많이 모여 있는지 "
    "확인하는 그래프입니다."
)


# ==================================================
# 2. 뇌졸중 경험 여부별 나이와 혈당 비교
# ==================================================
st.markdown("## 2. 뇌졸중 경험 여부에 따른 비교")

comparison = df[
    df["stroke"].isin([0, 1])
].copy()

comparison["뇌졸중 경험"] = comparison["stroke"].map({
    0: "겪지 않음 (stroke=0)",
    1: "겪음 (stroke=1)",
})

left, right = st.columns(2)

with left:
    age_box_data = comparison.dropna(
        subset=["age"]
    )

    fig_age_box = px.box(
        age_box_data,
        x="뇌졸중 경험",
        y="age",
        color="뇌졸중 경험",
        points="outliers",
        title="뇌졸중 경험 여부별 나이",
        labels={
            "age": "나이",
            "뇌졸중 경험": "뇌졸중 경험 여부",
        },
    )

    fig_age_box.update_layout(
        xaxis_title="뇌졸중 경험 여부",
        yaxis_title="나이",
        showlegend=False,
    )

    st.plotly_chart(
        fig_age_box,
        use_container_width=True,
    )

with right:
    glucose_box_data = comparison.dropna(
        subset=["avg_glucose_level"]
    )

    fig_glucose_box = px.box(
        glucose_box_data,
        x="뇌졸중 경험",
        y="avg_glucose_level",
        color="뇌졸중 경험",
        points="outliers",
        title="뇌졸중 경험 여부별 평균 혈당",
        labels={
            "avg_glucose_level": "평균 혈당",
            "뇌졸중 경험": "뇌졸중 경험 여부",
        },
    )

    fig_glucose_box.update_layout(
        xaxis_title="뇌졸중 경험 여부",
        yaxis_title="평균 혈당",
        showlegend=False,
    )

    st.plotly_chart(
        fig_glucose_box,
        use_container_width=True,
    )

# 두 집단의 평균값 표
mean_table = (
    comparison.groupby("뇌졸중 경험")
    .agg(
        사람_수=("stroke", "size"),
        평균_나이=("age", "mean"),
        평균_혈당=("avg_glucose_level", "mean"),
    )
    .reset_index()
    .rename(columns={
        "뇌졸중 경험": "뇌졸중 경험 여부",
        "사람_수": "사람 수",
        "평균_나이": "평균 나이",
        "평균_혈당": "평균 혈당",
    })
)

mean_table["평균 나이"] = (
    mean_table["평균 나이"].round(2)
)

mean_table["평균 혈당"] = (
    mean_table["평균 혈당"].round(2)
)

st.markdown("### 두 무리의 평균값")

st.dataframe(
    mean_table,
    use_container_width=True,
    hide_index=True,
)

st.caption(
    "상자그림으로 중앙값과 값의 퍼짐을 비교할 수 있습니다. "
    "관찰된 차이만으로 원인과 결과를 단정할 수는 없습니다."
)


# ==================================================
# 3. 고혈압과 심장병 여부별 뇌졸중 비율
# ==================================================
st.markdown("## 3. 건강 상태별 뇌졸중 비율")


def make_rate_table(data, column, label):
    subset = data[
        data[column].isin([0, 1])
        & data["stroke"].isin([0, 1])
    ].copy()

    result = (
        subset.groupby(column)
        .agg(
            전체_사람수=("stroke", "size"),
            뇌졸중_사람수=(
                "stroke",
                lambda s: int((s == 1).sum()),
            ),
            뇌졸중_비율=(
                "stroke",
                "mean",
            ),
        )
        .reset_index()
    )

    result[label] = result[column].map({
        0: "없음 (0)",
        1: "있음 (1)",
    })

    result["뇌졸중 비율(%)"] = (
        result["뇌졸중_비율"] * 100
    ).round(2)

    return result, label


left, right = st.columns(2)

with left:
    hypertension_table, hypertension_label = (
        make_rate_table(
            df,
            "hypertension",
            "고혈압 여부",
        )
    )

    fig_hypertension = px.bar(
        hypertension_table,
        x=hypertension_label,
        y="뇌졸중 비율(%)",
        text="뇌졸중 비율(%)",
        title="고혈압 여부별 뇌졸중 비율",
        labels={
            "뇌졸중 비율(%)": "뇌졸중 비율 (%)",
        },
    )

    fig_hypertension.update_traces(
        texttemplate="%{text:.2f}%",
        textposition="outside",
    )

    fig_hypertension.update_layout(
        yaxis_title="뇌졸중 비율 (%)",
        xaxis_title="고혈압",
    )

    st.plotly_chart(
        fig_hypertension,
        use_container_width=True,
    )

    st.dataframe(
        hypertension_table[
            [
                hypertension_label,
                "전체_사람수",
                "뇌졸중_사람수",
                "뇌졸중 비율(%)",
            ]
        ].rename(columns={
            "전체_사람수": "전체 사람 수",
            "뇌졸중_사람수": "뇌졸중 사람 수",
        }),
        use_container_width=True,
        hide_index=True,
    )

with right:
    heart_table, heart_label = make_rate_table(
        df,
        "heart_disease",
        "심장병 여부",
    )

    fig_heart = px.bar(
        heart_table,
        x=heart_label,
        y="뇌졸중 비율(%)",
        text="뇌졸중 비율(%)",
        title="심장병 여부별 뇌졸중 비율",
        labels={
            "뇌졸중 비율(%)": "뇌졸중 비율 (%)",
        },
    )

    fig_heart.update_traces(
        texttemplate="%{text:.2f}%",
        textposition="outside",
    )

    fig_heart.update_layout(
        yaxis_title="뇌졸중 비율 (%)",
        xaxis_title="심장병",
    )

    st.plotly_chart(
        fig_heart,
        use_container_width=True,
    )

    st.dataframe(
        heart_table[
            [
                heart_label,
                "전체_사람수",
                "뇌졸중_사람수",
                "뇌졸중 비율(%)",
            ]
        ].rename(columns={
            "전체_사람수": "전체 사람 수",
            "뇌졸중_사람수": "뇌졸중 사람 수",
        }),
        use_container_width=True,
        hide_index=True,
    )

st.caption(
    "비율은 각 집단에서 뇌졸중을 겪은 사람의 비율입니다. "
    "집단별 사람 수 차이도 함께 확인하세요."
)


# ==================================================
# 4. BMI 결측자와 전체 데이터의 뇌졸중 비율
# ==================================================
st.markdown(
    "## 4. BMI가 비어 있는 사람들의 뇌졸중 비율"
)

missing_bmi = df[df["bmi"].isna()]

missing_bmi_stroke = missing_bmi[
    missing_bmi["stroke"].isin([0, 1])
]

valid_stroke = df[
    df["stroke"].isin([0, 1])
]

missing_bmi_count = len(missing_bmi)

missing_bmi_rate = (
    (missing_bmi_stroke["stroke"] == 1).mean() * 100
    if len(missing_bmi_stroke) > 0
    else float("nan")
)

overall_rate = (
    (valid_stroke["stroke"] == 1).mean() * 100
    if len(valid_stroke) > 0
    else float("nan")
)

bmi_missing_table = pd.DataFrame([
    {
        "대상": "BMI가 비어 있는 사람",
        "사람 수": missing_bmi_count,
        "뇌졸중 여부 확인 가능 인원": len(
            missing_bmi_stroke
        ),
        "뇌졸중 사람 수": int(
            (missing_bmi_stroke["stroke"] == 1).sum()
        ),
        "뇌졸중 비율(%)": (
            round(missing_bmi_rate, 2)
            if pd.notna(missing_bmi_rate)
            else None
        ),
    },
    {
        "대상": "전체 데이터",
        "사람 수": len(df),
        "뇌졸중 여부 확인 가능 인원": len(
            valid_stroke
        ),
        "뇌졸중 사람 수": int(
            (valid_stroke["stroke"] == 1).sum()
        ),
        "뇌졸중 비율(%)": (
            round(overall_rate, 2)
            if pd.notna(overall_rate)
            else None
        ),
    },
])

st.write(
    "BMI가 비어 있다는 사실 자체가 뇌졸중을 의미하지는 않습니다. "
    "두 집단의 비율을 비교해 보세요."
)

st.dataframe(
    bmi_missing_table,
    use_container_width=True,
    hide_index=True,
)


# ==================================================
# 5. 흡연 상태별 사람 수
# ==================================================
st.markdown("## 5. 흡연 상태별 사람 수")

smoking_counts = (
    df["smoking_status"]
    .fillna("결측값")
    .astype(str)
    .value_counts(dropna=False)
    .rename_axis("흡연 상태")
    .reset_index(name="사람 수")
)

st.dataframe(
    smoking_counts,
    use_container_width=True,
    hide_index=True,
)

st.caption(
    "흡연 상태가 비어 있는 경우는 '결측값'으로 따로 집계했습니다."
)
