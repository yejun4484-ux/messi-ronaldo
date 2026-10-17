# pages/3_채점표.py
# 채점용 데이터로 두 모델의 혼동행렬과 성능 지표를 비교한다.

import pandas as pd
import streamlit as st

from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from sklearn.tree import DecisionTreeClassifier


DATA_URL = (
    "https://raw.githubusercontent.com/greatsong/"
    "modudata/main/data/stroke.csv"
)

st.set_page_config(
    page_title="채점표",
    page_icon="📋",
    layout="wide",
)

st.title("📋 채점표")
st.write(
    "채점용 사람들의 실제 뇌졸중 여부와 모델의 예측을 비교합니다. "
    "혼동행렬과 네 가지 성능 지표를 확인하고, "
    "놓친 환자와 헛짚은 사람도 살펴봅니다."
)

# --------------------------------------------------
# 1. 데이터 읽기 및 전처리
# --------------------------------------------------
@st.cache_data
def load_data():
    df = pd.read_csv(DATA_URL, encoding="utf-8")

    required_columns = [
        "id",
        "age",
        "avg_glucose_level",
        "hypertension",
        "heart_disease",
        "stroke",
        "bmi",
    ]

    missing_columns = [
        col for col in required_columns if col not in df.columns
    ]

    if missing_columns:
        raise ValueError(
            f"데이터에 필요한 열이 없습니다: {missing_columns}"
        )

    for col in required_columns:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    df = df.dropna(
        subset=[
            "id",
            "age",
            "avg_glucose_level",
            "hypertension",
            "heart_disease",
            "stroke",
        ]
    )

    df = df[df["stroke"].isin([0, 1])].copy()
    df["stroke"] = df["stroke"].astype(int)

    # 분류 모델 페이지와 같은 방식으로 id 정렬
    df = df.sort_values("id").reset_index(drop=True)

    return df


try:
    df = load_data()
except Exception as e:
    st.error(f"데이터를 불러오지 못했습니다: {e}")
    st.stop()


# --------------------------------------------------
# 2. 사용할 속성 선택
# --------------------------------------------------
st.subheader("1. 모델에 사용할 속성")

feature_options = [
    "age",
    "avg_glucose_level",
    "bmi",
    "hypertension",
    "heart_disease",
]

feature_names = {
    "age": "나이",
    "avg_glucose_level": "평균 혈당",
    "bmi": "BMI",
    "hypertension": "고혈압 여부",
    "heart_disease": "심장병 여부",
}

selected_features = st.multiselect(
    "학습에 사용할 속성 (최소 2개)",
    options=feature_options,
    default=[
        "age",
        "avg_glucose_level",
        "hypertension",
        "heart_disease",
    ],
    format_func=lambda x: feature_names[x],
)

if len(selected_features) < 2:
    st.warning("모델을 학습하려면 속성을 2개 이상 선택하세요.")
    st.stop()


# --------------------------------------------------
# 3. 훈련용과 채점용 데이터 나누기
#    정렬된 데이터에서 10명 중 처음 3명은 채점용
# --------------------------------------------------
test_mask = df.index % 10 < 3

train_df = df.loc[~test_mask].copy()
test_df = df.loc[test_mask].copy()

if train_df.empty or test_df.empty:
    st.error("훈련용 또는 채점용 데이터가 없습니다.")
    st.stop()

X_train = train_df[selected_features].copy()
X_test = test_df[selected_features].copy()

y_train = train_df["stroke"].astype(int)
y_test = test_df["stroke"].astype(int)

# BMI 결측치는 훈련용 BMI의 중앙값으로 채운다.
# 채점용 데이터의 값은 중앙값 계산에 사용하지 않는다.
if "bmi" in selected_features:
    bmi_median = X_train["bmi"].median()

    if pd.isna(bmi_median):
        st.error("훈련용 BMI에 사용할 수 있는 값이 없습니다.")
        st.stop()

    X_train["bmi"] = X_train["bmi"].fillna(bmi_median)
    X_test["bmi"] = X_test["bmi"].fillna(bmi_median)

# 나머지 속성에 결측치가 있는 경우 학습을 중단한다.
if X_train.isna().any().any() or X_test.isna().any().any():
    st.error("선택한 속성에 처리되지 않은 결측치가 있습니다.")
    st.stop()


# --------------------------------------------------
# 4. 두 모델 학습
# --------------------------------------------------
# 모델 1: 표준화 + 로지스틱 회귀
scaler = StandardScaler()
X_train_scaled = scaler.fit_transform(X_train)
X_test_scaled = scaler.transform(X_test)

logistic_model = LogisticRegression(
    max_iter=1000,
    random_state=0,
)
logistic_model.fit(X_train_scaled, y_train)

# 모델 2: 결정 트리
tree_model = DecisionTreeClassifier(
    max_depth=3,
    min_samples_leaf=5,
    random_state=0,
)
tree_model.fit(X_train, y_train)

# 채점용 데이터 예측
predictions = {
    "로지스틱 회귀": logistic_model.predict(X_test_scaled).astype(int),
    "결정 트리": tree_model.predict(X_test).astype(int),
}

# 훈련용에서 더 많은 클래스를 항상 예측하는 기준 모델
# 동률이면 0을 선택한다.
train_counts = y_train.value_counts()
majority_class = (
    1 if train_counts.get(1, 0) > train_counts.get(0, 0) else 0
)

predictions["훈련용 다수 클래스 기준"] = [
    majority_class
] * len(y_test)


# --------------------------------------------------
# 5. 혼동행렬과 성능 지표 계산
# --------------------------------------------------
def get_confusion(y_true, y_pred):
    y_true = list(y_true)
    y_pred = list(y_pred)

    tn = sum(
        actual == 0 and pred == 0
        for actual, pred in zip(y_true, y_pred)
    )
    fp = sum(
        actual == 0 and pred == 1
        for actual, pred in zip(y_true, y_pred)
    )
    fn = sum(
        actual == 1 and pred == 0
        for actual, pred in zip(y_true, y_pred)
    )
    tp = sum(
        actual == 1 and pred == 1
        for actual, pred in zip(y_true, y_pred)
    )

    return {"TP": tp, "FP": fp, "FN": fn, "TN": tn}


def get_metrics(cm):
    tp = cm["TP"]
    fp = cm["FP"]
    fn = cm["FN"]
    tn = cm["TN"]

    total = tp + fp + fn + tn
    predicted_positive = tp + fp
    actual_positive = tp + fn

    accuracy = (tp + tn) / total if total else 0.0

    # 예측 양성이 0명일 때 정밀도는 계산할 수 없다.
    precision = (
        tp / predicted_positive
        if predicted_positive > 0
        else None
    )

    recall = (
        tp / actual_positive
        if actual_positive > 0
        else 0.0
    )

    # F1 = 2TP / (2TP + FP + FN)
    f1_denominator = 2 * tp + fp + fn
    f1 = (
        2 * tp / f1_denominator
        if f1_denominator > 0
        else 0.0
    )

    return {
        "정확도": accuracy,
        "정밀도": precision,
        "재현율": recall,
        "F1": f1,
    }


# ★ 오류 수정: 실제 정답 y_test와 예측 pred를 모두 전달한다.
confusion_results = {
    name: get_confusion(y_test, pred)
    for name, pred in predictions.items()
}

metric_results = {
    name: get_metrics(cm)
    for name, cm in confusion_results.items()
}


# --------------------------------------------------
# 6. 채점용 데이터 규모
# --------------------------------------------------
st.subheader("2. 채점용 데이터")

test_people = len(test_df)
test_stroke_people = int((y_test == 1).sum())

st.markdown(
    f"**채점용 사람 수: {test_people:,}명 · "
    f"그중 실제 뇌졸중인 사람: {test_stroke_people:,}명**"
)

st.caption(
    f"훈련용 {len(train_df):,}명으로 학습하고, "
    f"채점용 {test_people:,}명으로 평가했습니다. "
    f"훈련용 다수 클래스 기준 모델은 "
    f"{'뇌졸중' if majority_class == 1 else '뇌졸중 아님'}만 예측합니다."
)


# --------------------------------------------------
# 7. 모델별 혼동행렬
# --------------------------------------------------
st.subheader("3. 혼동행렬")

st.write(
    "행은 실제 상태, 열은 모델의 예측입니다. "
    "0은 뇌졸중 아님, 1은 뇌졸중입니다."
)


def make_confusion_table(cm):
    tn = cm["TN"]
    fp = cm["FP"]
    fn = cm["FN"]
    tp = cm["TP"]

    return pd.DataFrame(
        [
            [
                f"TN: {tn:,}명",
                f"FP: {fp:,}명",
                f"{tn + fp:,}명",
            ],
            [
                f"FN: {fn:,}명",
                f"TP: {tp:,}명",
                f"{fn + tp:,}명",
            ],
            [
                f"{tn + fn:,}명",
                f"{fp + tp:,}명",
                f"{tn + fp + fn + tp:,}명",
            ],
        ],
        index=[
            "실제 뇌졸중 아님 (0)",
            "실제 뇌졸중 (1)",
            "열 합계",
        ],
        columns=[
            "예측 뇌졸중 아님 (0)",
            "예측 뇌졸중 (1)",
            "행 합계",
        ],
    )


col1, col2 = st.columns(2)

with col1:
    st.markdown("**로지스틱 회귀**")
    st.dataframe(
        make_confusion_table(confusion_results["로지스틱 회귀"]),
        use_container_width=True,
    )

with col2:
    st.markdown("**결정 트리**")
    st.dataframe(
        make_confusion_table(confusion_results["결정 트리"]),
        use_container_width=True,
    )

with st.expander("훈련용 다수 클래스 기준 모델의 혼동행렬 보기"):
    st.dataframe(
        make_confusion_table(
            confusion_results["훈련용 다수 클래스 기준"]
        ),
        use_container_width=True,
    )

st.caption(
    "TP: 실제 뇌졸중을 뇌졸중으로 예측 · "
    "TN: 실제 뇌졸중 아님을 뇌졸중 아님으로 예측 · "
    "FP: 실제 뇌졸중 아님을 뇌졸중으로 예측 · "
    "FN: 실제 뇌졸중을 뇌졸중 아님으로 예측"
)


# --------------------------------------------------
# 8. 세 모델의 성능 지표 비교
# --------------------------------------------------
st.subheader("4. 성능 지표 비교")

metric_rows = []

for name in [
    "로지스틱 회귀",
    "결정 트리",
    "훈련용 다수 클래스 기준",
]:
    metrics = metric_results[name]

    precision_text = (
        "계산할 수 없음"
        if metrics["정밀도"] is None
        else f"{metrics['정밀도']:.2%}"
    )

    metric_rows.append({
        "모델": name,
        "정확도": f"{metrics['정확도']:.2%}",
        "정밀도": precision_text,
        "재현율": f"{metrics['재현율']:.2%}",
        "F1": f"{metrics['F1']:.2%}",
    })

st.dataframe(
    pd.DataFrame(metric_rows),
    hide_index=True,
    use_container_width=True,
)

st.markdown(
    """
    - **정확도** = (TP + TN) / 전체 사람 수
    - **정밀도** = TP / (TP + FP)
    - **재현율** = TP / (TP + FN)
    - **F1** = 2 × TP / (2 × TP + FP + FN)
    """
)

st.caption(
    "정밀도는 뇌졸중이라고 예측한 사람 중 실제 뇌졸중인 비율입니다. "
    "재현율은 실제 뇌졸중인 사람 중 모델이 찾아낸 비율입니다. "
    "F1은 정밀도와 재현율을 함께 고려합니다."
)


# --------------------------------------------------
# 9. 놓친 환자와 헛짚은 사람 목록
# --------------------------------------------------
st.subheader("5. 놓친 환자와 헛짚은 사람")

selected_model = st.selectbox(
    "목록을 확인할 모델",
    options=[
        "로지스틱 회귀",
        "결정 트리",
        "훈련용 다수 클래스 기준",
    ],
)

selected_predictions = predictions[selected_model]

# 원래 데이터의 행 인덱스를 유지하여 사람별 예측을 연결한다.
result_df = test_df.copy()
result_df["실제"] = y_test.to_numpy()
result_df["예측"] = selected_predictions

# FN: 실제 1, 예측 0
missed = result_df[
    (result_df["실제"] == 1) & (result_df["예측"] == 0)
].copy()

# FP: 실제 0, 예측 1
false_alarms = result_df[
    (result_df["실제"] == 0) & (result_df["예측"] == 1)
].copy()

missed = missed.sort_values("age", ascending=False)
false_alarms = false_alarms.sort_values("age", ascending=False)


def make_people_table(people):
    display_df = pd.DataFrame({
        "번호": range(1, len(people) + 1),
        "나이": people["age"].to_numpy(),
        "평균 혈당": people["avg_glucose_level"].to_numpy(),
        "고혈압 여부": people["hypertension"].map(
            {0: "아니요", 1: "예"}
        ).to_numpy(),
        "심장병 여부": people["heart_disease"].map(
            {0: "아니요", 1: "예"}
        ).to_numpy(),
    })

    display_df["나이"] = display_df["나이"].map(
        lambda x: f"{x:g}" if pd.notna(x) else "알 수 없음"
    )
    display_df["평균 혈당"] = display_df["평균 혈당"].map(
        lambda x: f"{x:.2f}" if pd.notna(x) else "알 수 없음"
    )

    return display_df.head(20)


left, right = st.columns(2)

with left:
    st.markdown(f"**놓친 환자: {len(missed):,}명 (FN)**")
    st.caption("실제 뇌졸중이지만 뇌졸중이 아니라고 예측한 사람")

    if missed.empty:
        st.info("놓친 환자가 없습니다.")
    else:
        st.dataframe(
            make_people_table(missed),
            hide_index=True,
            use_container_width=True,
        )

    if len(missed) > 20:
        st.caption(
            f"전체 {len(missed):,}명 중 나이가 많은 순서로 "
            "앞의 20명만 표시했습니다."
        )

with right:
    st.markdown(f"**헛짚은 사람: {len(false_alarms):,}명 (FP)**")
    st.caption("실제 뇌졸중이 아니지만 뇌졸중이라고 예측한 사람")

    if false_alarms.empty:
        st.info("헛짚은 사람이 없습니다.")
    else:
        st.dataframe(
            make_people_table(false_alarms),
            hide_index=True,
            use_container_width=True,
        )

    if len(false_alarms) > 20:
        st.caption(
            f"전체 {len(false_alarms):,}명 중 나이가 많은 순서로 "
            "앞의 20명만 표시했습니다."
        )

st.info(
    f"목록 인원 확인: 놓친 환자 {len(missed):,}명 = "
    f"혼동행렬 FN {confusion_results[selected_model]['FN']:,}명, "
    f"헛짚은 사람 {len(false_alarms):,}명 = "
    f"혼동행렬 FP {confusion_results[selected_model]['FP']:,}명."
)
