
# pages/4_전처리.py
# 클래스 무게 균형 적용 전후의 분류 모델 성능과 결정 경계를 비교한다.

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from sklearn.tree import DecisionTreeClassifier


DATA_URL = (
    "https://raw.githubusercontent.com/greatsong/"
    "modudata/main/data/stroke.csv"
)

FEATURE_OPTIONS = [
    "age",
    "avg_glucose_level",
    "bmi",
    "hypertension",
    "heart_disease",
]

FEATURE_LABELS = {
    "age": "나이",
    "avg_glucose_level": "평균 혈당",
    "bmi": "BMI",
    "hypertension": "고혈압 여부",
    "heart_disease": "심장병 여부",
}

st.set_page_config(
    page_title="전처리",
    page_icon="⚖️",
    layout="wide",
)

st.title("⚖️ 전처리 실험실")
st.write(
    "클래스 무게 균형과 결측치 처리 방법에 따라 "
    "뇌졸중 분류 결과가 어떻게 달라지는지 비교합니다."
)


# ==================================================
# 1. 화면 맨 위의 세 가지 선택
# ==================================================
st.subheader("실험 조건")

balance_switch = st.toggle(
    "클래스 무게 균형 적용",
    value=False,
    help=(
        "켜면 환자 수가 적은 뇌졸중 클래스에 더 큰 무게를 주는 "
        "모델의 결과를 놓친 환자 목록에 사용합니다. "
        "비교표에는 적용 전과 후의 결과를 항상 모두 표시합니다."
    ),
)

bmi_action = st.radio(
    "BMI가 비어 있는 사람",
    options=["그대로 두기", "삭제하기"],
    horizontal=True,
    help=(
        "삭제하기를 선택하면 채점용과 훈련용 데이터에서 "
        "BMI 결측 행을 제거합니다. 그대로 두기는 BMI를 입력 항목으로 "
        "사용할 때 훈련용 BMI의 중앙값으로 채웁니다."
    ),
)

selected_features = st.multiselect(
    "입력으로 사용할 항목",
    options=FEATURE_OPTIONS,
    default=[
        "age",
        "avg_glucose_level",
        "hypertension",
        "heart_disease",
    ],
    format_func=lambda x: FEATURE_LABELS[x],
)

if len(selected_features) < 2:
    st.warning("입력 항목을 2개 이상 선택하세요.")
    st.stop()


# ==================================================
# 2. 데이터 읽기
# ==================================================
@st.cache_data
def load_data():
    data = pd.read_csv(DATA_URL, encoding="utf-8")

    required = [
        "id",
        "age",
        "avg_glucose_level",
        "hypertension",
        "heart_disease",
        "stroke",
        "bmi",
    ]

    missing_columns = [
        col for col in required if col not in data.columns
    ]

    if missing_columns:
        raise ValueError(
            f"필요한 열이 없습니다: {missing_columns}"
        )

    for col in required:
        data[col] = pd.to_numeric(data[col], errors="coerce")

    data = data.dropna(
        subset=[
            "id",
            "age",
            "avg_glucose_level",
            "hypertension",
            "heart_disease",
            "stroke",
        ]
    ).copy()

    data = data[data["stroke"].isin([0, 1])].copy()
    data["stroke"] = data["stroke"].astype(int)

    return data.sort_values("id").reset_index(drop=True)


try:
    df = load_data()
except Exception as e:
    st.error(f"데이터를 읽는 중 오류가 발생했습니다: {e}")
    st.stop()


# ==================================================
# 3. 채점용과 훈련용 분리
#    채점표 페이지와 동일하게 id 정렬 후 10명 중 3명
# ==================================================
test_mask = df.index % 10 < 3

train_df = df.loc[~test_mask].copy()
test_df = df.loc[test_mask].copy()

# BMI 삭제를 선택하면 분리된 두 집합에서 각각 결측 행 제거
if bmi_action == "삭제하기":
    deleted_count = int(df["bmi"].isna().sum())
    deleted_stroke_count = int(
        ((df["bmi"].isna()) & (df["stroke"] == 1)).sum()
    )

    train_df = train_df.dropna(subset=["bmi"]).copy()
    test_df = test_df.dropna(subset=["bmi"]).copy()

    st.info(
        f"BMI 결측으로 삭제한 사람: {deleted_count:,}명 · "
        f"그중 뇌졸중 환자: {deleted_stroke_count:,}명"
    )
else:
    st.caption(
        "BMI 결측 행을 유지했습니다. BMI를 입력 항목으로 선택한 경우에만 "
        "훈련용 데이터의 중앙값으로 결측치를 채웁니다."
    )

if train_df.empty or test_df.empty:
    st.error("훈련용 또는 채점용 데이터가 없습니다.")
    st.stop()

X_train = train_df[selected_features].copy()
X_test = test_df[selected_features].copy()

y_train = train_df["stroke"].astype(int)
y_test = test_df["stroke"].astype(int)

# BMI가 입력 항목일 때만 중앙값 대체
if "bmi" in selected_features:
    bmi_median = X_train["bmi"].median()

    if pd.isna(bmi_median):
        st.error("훈련용 BMI에 사용할 수 있는 값이 없습니다.")
        st.stop()

    X_train["bmi"] = X_train["bmi"].fillna(bmi_median)
    X_test["bmi"] = X_test["bmi"].fillna(bmi_median)

if X_train.isna().any().any() or X_test.isna().any().any():
    st.error("선택한 입력 항목에 처리되지 않은 결측치가 있습니다.")
    st.stop()

if y_train.nunique() < 2:
    st.error("훈련용 데이터에 뇌졸중 여부 두 종류가 모두 있어야 합니다.")
    st.stop()


# ==================================================
# 4. 무게 균형 적용 전후의 두 모델 학습
# ==================================================
scaler = StandardScaler()
X_train_scaled = scaler.fit_transform(X_train)
X_test_scaled = scaler.transform(X_test)

# 로지스틱 회귀: 적용 전
logistic_before = LogisticRegression(
    max_iter=1000,
    random_state=0,
)
logistic_before.fit(X_train_scaled, y_train)

# 로지스틱 회귀: 적용 후
logistic_after = LogisticRegression(
    max_iter=1000,
    class_weight="balanced",
    random_state=0,
)
logistic_after.fit(X_train_scaled, y_train)

# 결정 트리: 적용 전
tree_before = DecisionTreeClassifier(
    max_depth=3,
    min_samples_leaf=5,
    random_state=0,
)
tree_before.fit(X_train, y_train)

# 결정 트리: 적용 후
tree_after = DecisionTreeClassifier(
    max_depth=3,
    min_samples_leaf=5,
    class_weight="balanced",
    random_state=0,
)
tree_after.fit(X_train, y_train)

# 예측값은 동일한 채점용 데이터에서 비교
predictions = {
    "로지스틱 회귀": {
        "적용 전": logistic_before.predict(X_test_scaled).astype(int),
        "적용 후": logistic_after.predict(X_test_scaled).astype(int),
    },
    "결정 트리": {
        "적용 전": tree_before.predict(X_test).astype(int),
        "적용 후": tree_after.predict(X_test).astype(int),
    },
}

# 확률로 답하는 모델(로지스틱 회귀)의 뇌졸중 예측 확률
probabilities = {
    "적용 전": logistic_before.predict_proba(X_test_scaled)[:, 1],
    "적용 후": logistic_after.predict_proba(X_test_scaled)[:, 1],
}


# ==================================================
# 5. 혼동행렬과 지표 계산
# ==================================================
def confusion_counts(actual, predicted):
    actual = np.asarray(actual)
    predicted = np.asarray(predicted)

    tp = int(((actual == 1) & (predicted == 1)).sum())
    fp = int(((actual == 0) & (predicted == 1)).sum())
    fn = int(((actual == 1) & (predicted == 0)).sum())
    tn = int(((actual == 0) & (predicted == 0)).sum())

    return {"TP": tp, "FP": fp, "FN": fn, "TN": tn}


def calculate_metrics(cm):
    tp = cm["TP"]
    fp = cm["FP"]
    fn = cm["FN"]
    tn = cm["TN"]

    total = tp + fp + fn + tn

    accuracy = (tp + tn) / total if total else 0.0

    precision = tp / (tp + fp) if tp + fp > 0 else None
    recall = tp / (tp + fn) if tp + fn > 0 else 0.0

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


results = {}

for model_name, versions in predictions.items():
    results[model_name] = {}

    for version, predicted in versions.items():
        cm = confusion_counts(y_test, predicted)
        metrics = calculate_metrics(cm)

        results[model_name][version] = {
            "cm": cm,
            "metrics": metrics,
            "predicted": predicted,
        }


def pct(value):
    if value is None:
        return "계산할 수 없음"
    return f"{value:.2%}"


def confusion_table(cm):
    return pd.DataFrame(
        [
            [
                f"TN: {cm['TN']:,}명",
                f"FP: {cm['FP']:,}명",
                f"{cm['TN'] + cm['FP']:,}명",
            ],
            [
                f"FN: {cm['FN']:,}명",
                f"TP: {cm['TP']:,}명",
                f"{cm['FN'] + cm['TP']:,}명",
            ],
            [
                f"{cm['TN'] + cm['FN']:,}명",
                f"{cm['FP'] + cm['TP']:,}명",
                f"{sum(cm.values()):,}명",
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


def metric_table(metrics):
    return pd.DataFrame(
        [
            {"지표": name, "값": pct(metrics[name])}
            for name in ["정확도", "정밀도", "재현율", "F1"]
        ]
    )


# ==================================================
# 6. 데이터 규모
# ==================================================
st.subheader("1. 데이터 나누기")

st.markdown(
    f"**훈련용: {len(train_df):,}명 · "
    f"채점용: {len(test_df):,}명 · "
    f"채점용 실제 뇌졸중 환자: {(y_test == 1).sum():,}명**"
)

st.caption(
    "분리 기준은 id 정렬 후 10명 중 앞의 3명을 채점용으로 지정하는 것입니다. "
    "BMI 결측 행을 삭제한 경우 실제 학습·평가 인원은 줄어듭니다."
)

st.subheader("2. 혼동행렬과 성능 지표")

st.write(
    "각 모델의 무게 균형 적용 전과 후를 같은 채점용 데이터에서 비교합니다. "
    "혼동행렬의 행은 실제 상태, 열은 예측 상태입니다."
)

for model_name in ["로지스틱 회귀", "결정 트리"]:
    st.markdown(f"### {model_name}")

    before = results[model_name]["적용 전"]
    after = results[model_name]["적용 후"]

    left, right = st.columns(2)

    with left:
        st.markdown("**무게 균형 적용 전**")
        st.dataframe(
            confusion_table(before["cm"]),
            use_container_width=True,
        )
        st.dataframe(
            metric_table(before["metrics"]),
            hide_index=True,
            use_container_width=True,
        )

    with right:
        st.markdown("**무게 균형 적용 후**")
        st.dataframe(
            confusion_table(after["cm"]),
            use_container_width=True,
        )
        st.dataframe(
            metric_table(after["metrics"]),
            hide_index=True,
            use_container_width=True,
        )

    st.caption(
        f"찾아낸 환자(TP): {before['cm']['TP']:,}명 → "
        f"{after['cm']['TP']:,}명 · "
        f"놓친 환자(FN): {before['cm']['FN']:,}명 → "
        f"{after['cm']['FN']:,}명 · "
        f"헛짚은 사람(FP): {before['cm']['FP']:,}명 → "
        f"{after['cm']['FP']:,}명"
    )

st.caption(
    "TP: 실제 뇌졸중을 뇌졸중으로 예측 · "
    "TN: 실제 뇌졸중 아님을 뇌졸중 아님으로 예측 · "
    "FP: 실제 뇌졸중 아님을 뇌졸중으로 예측 · "
    "FN: 실제 뇌졸중을 뇌졸중 아님으로 예측"
)

st.markdown(
    """
    - 정확도 = (TP + TN) / 전체 사람 수
    - 정밀도 = TP / (TP + FP)
    - 재현율 = TP / (TP + FN)
    - F1 = 2 × TP / (2 × TP + FP + FN)
    """
)


# ==================================================
# 7. 결정 경계용 보조 함수
# ==================================================
st.subheader("3. 산점도와 0.5 결정 경계")

st.write(
    "점의 색은 실제 뇌졸중 여부를 나타냅니다. "
    "경계선과 경계 평면은 로지스틱 회귀가 뇌졸중일 확률을 "
    "0.5로 예측하는 위치입니다. "
    "다른 입력 항목이 선택되어 있으면 그 항목은 훈련용 중앙값으로 고정합니다."
)

plot_features = selected_features[:3]
plot_labels = [FEATURE_LABELS[f] for f in plot_features]

# 원래 채점용 특성의 실제 값을 사용하되,
# BMI 결측을 유지한 상태에서도 시각화할 수 있게 중앙값으로 채운다.
plot_df = test_df.copy()

for feature in plot_features:
    if feature == "bmi":
        plot_df[feature] = plot_df[feature].fillna(
            train_df["bmi"].median()
            if train_df["bmi"].notna().any()
            else 0
        )

# 삭제 모드가 아니더라도 실제 입력 X_test와 동일한 전처리값을 사용
plot_X = X_test.copy()

if plot_X.isna().any().any():
    st.error("산점도에 사용할 값의 결측치를 처리하지 못했습니다.")
    st.stop()

if len(plot_features) == 2:
    x_feature, y_feature = plot_features
    x_label, y_label = plot_labels

    fig = go.Figure()

    for label, color, name in [
        (0, "#2878B5", "실제 뇌졸중 아님"),
        (1, "#D94841", "실제 뇌졸중"),
    ]:
        mask = y_test.to_numpy() == label

        fig.add_trace(
            go.Scatter(
                x=plot_X.loc[mask, x_feature],
                y=plot_X.loc[mask, y_feature],
                mode="markers",
                name=name,
                marker=dict(
                    color=color,
                    size=7,
                    opacity=0.7,
                ),
                text=[
                    f"실제: {'뇌졸중' if label == 1 else '뇌졸중 아님'}"
                ] * int(mask.sum()),
                hovertemplate=(
                    f"{x_label}: %{{x}}<br>"
                    f"{y_label}: %{{y}}<br>"
                    "%{text}<extra></extra>"
                ),
            )
        )

    x_min = float(plot_X[x_feature].min())
    x_max = float(plot_X[x_feature].max())
    y_min = float(plot_X[y_feature].min())
    y_max = float(plot_X[y_feature].max())

    x_pad = max((x_max - x_min) * 0.05, 0.1)
    y_pad = max((y_max - y_min) * 0.05, 0.1)

    x_min -= x_pad
    x_max += x_pad
    y_min -= y_pad
    y_max += y_pad

    # 로지스틱 회귀의 경계는 원래 단위 좌표에서 계산한다.
    # 나머지 입력은 훈련용 중앙값으로 고정한다.
    median_row = X_train.median(numeric_only=True)

    def boundary_2d(model):
        coef = model.coef_[0]
        intercept = float(model.intercept_[0])

        scaled_medians = scaler.transform(
            pd.DataFrame(
                [median_row.reindex(selected_features).to_dict()],
                columns=selected_features,
            )
        )[0]

        x_idx = selected_features.index(x_feature)
        y_idx = selected_features.index(y_feature)

        fixed_contribution = intercept

        for i, feature in enumerate(selected_features):
            if feature not in (x_feature, y_feature):
                fixed_contribution += coef[i] * scaled_medians[i]

        # 표준화 좌표에서 계수 변환:
        # z = (원래값 - 평균) / 표준편차
        x_scale = scaler.scale_[x_idx]
        y_scale = scaler.scale_[y_idx]

        a = coef[x_idx] / x_scale
        b = coef[y_idx] / y_scale

        c = fixed_contribution - (
            coef[x_idx] * scaler.mean_[x_idx] / x_scale
        ) - (
            coef[y_idx] * scaler.mean_[y_idx] / y_scale
        )

        return a, b, c

    boundary_messages = []

    for version, model, color, dash in [
        ("무게 균형 적용 전", logistic_before, "#E69500", "solid"),
        ("무게 균형 적용 후", logistic_after, "#7B4AB5", "dash"),
    ]:
        a, b, c = boundary_2d(model)
        line_x = np.linspace(x_min, x_max, 250)

        if abs(b) > 1e-12:
            line_y = -(a * line_x + c) / b

            inside = (
                (line_y >= y_min) &
                (line_y <= y_max)
            )

            if inside.any():
                fig.add_trace(
                    go.Scatter(
                        x=line_x[inside],
                        y=line_y[inside],
                        mode="lines",
                        name=f"{version} 0.5 경계",
                        line=dict(color=color, width=3, dash=dash),
                    )
                )
            else:
                boundary_messages.append(
                    f"{version}의 0.5 경계선은 현재 그림 범위 밖에 있습니다."
                )

        elif abs(a) > 1e-12:
            vertical_x = -c / a

            if x_min <= vertical_x <= x_max:
                fig.add_trace(
                    go.Scatter(
                        x=[vertical_x, vertical_x],
                        y=[y_min, y_max],
                        mode="lines",
                        name=f"{version} 0.5 경계",
                        line=dict(color=color, width=3, dash=dash),
                    )
                )
            else:
                boundary_messages.append(
                    f"{version}의 0.5 경계선은 현재 그림 범위 밖에 있습니다."
                )
        else:
            boundary_messages.append(
                f"{version}의 0.5 경계선은 표시할 수 없는 형태입니다."
            )

    fig.update_layout(
        xaxis_title=x_label,
        yaxis_title=y_label,
        height=620,
        legend_title="범례",
        hovermode="closest",
    )

    st.plotly_chart(fig, use_container_width=True)

    for message in boundary_messages:
        st.warning(message)

elif len(plot_features) >= 3:
    x_feature, y_feature, z_feature = plot_features
    x_label, y_label, z_label = plot_labels

    fig = go.Figure()

    for label, color, name in [
        (0, "#2878B5", "실제 뇌졸중 아님"),
        (1, "#D94841", "실제 뇌졸중"),
    ]:
        mask = y_test.to_numpy() == label

        fig.add_trace(
            go.Scatter3d(
                x=plot_X.loc[mask, x_feature],
                y=plot_X.loc[mask, y_feature],
                z=plot_X.loc[mask, z_feature],
                mode="markers",
                name=name,
                marker=dict(
                    color=color,
                    size=4,
                    opacity=0.7,
                ),
                hovertemplate=(
                    f"{x_label}: %{{x}}<br>"
                    f"{y_label}: %{{y}}<br>"
                    f"{z_label}: %{{z}}<br>"
                    f"실제: {'뇌졸중' if label == 1 else '뇌졸중 아님'}"
                    "<extra></extra>"
                ),
            )
        )

    x_min, x_max = float(plot_X[x_feature].min()), float(plot_X[x_feature].max())
    y_min, y_max = float(plot_X[y_feature].min()), float(plot_X[y_feature].max())
    z_min, z_max = float(plot_X[z_feature].min()), float(plot_X[z_feature].max())

    x_pad = max((x_max - x_min) * 0.05, 0.1)
    y_pad = max((y_max - y_min) * 0.05, 0.1)
    z_pad = max((z_max - z_min) * 0.05, 0.1)

    x_min, x_max = x_min - x_pad, x_max + x_pad
    y_min, y_max = y_min - y_pad, y_max + y_pad
    z_min, z_max = z_min - z_pad, z_max + z_pad

    median_row = X_train.median(numeric_only=True)
    grid_x = np.linspace(x_min, x_max, 25)
    grid_y = np.linspace(y_min, y_max, 25)
    gx, gy = np.meshgrid(grid_x, grid_y)

    boundary_messages = []

    for version, model, color in [
        ("무게 균형 적용 전", logistic_before, "#E69500"),
        ("무게 균형 적용 후", logistic_after, "#7B4AB5"),
    ]:
        coef = model.coef_[0]
        intercept = float(model.intercept_[0])

        indices = [
            selected_features.index(f)
            for f in [x_feature, y_feature, z_feature]
        ]

        # 표준화된 모델의 계수를 원래 좌표계로 변환
        a, b, c = [
            coef[i] / scaler.scale_[i]
            for i in indices
        ]

        fixed = intercept

        for i, feature in enumerate(selected_features):
            if feature not in (x_feature, y_feature, z_feature):
                fixed += coef[i] * (
                    median_row[feature] - scaler.mean_[i]
                ) / scaler.scale_[i]

        fixed -= (
            coef[indices[0]] * scaler.mean_[indices[0]]
            / scaler.scale_[indices[0]]
        )
        fixed -= (
            coef[indices[1]] * scaler.mean_[indices[1]]
            / scaler.scale_[indices[1]]
        )
        fixed -= (
            coef[indices[2]] * scaler.mean_[indices[2]]
            / scaler.scale_[indices[2]]
        )

        if abs(c) > 1e-12:
            gz = -(a * gx + b * gy + fixed) / c
            inside = (gz >= z_min) & (gz <= z_max)

            if inside.any():
                surface_z = np.where(inside, gz, np.nan)

                fig.add_trace(
                    go.Surface(
                        x=gx,
                        y=gy,
                        z=surface_z,
                        name=f"{version} 0.5 경계 평면",
                        showscale=False,
                        opacity=0.35,
                        colorscale=[
                            [0, color],
                            [1, color],
                        ],
                        hoverinfo="skip",
                    )
                )
            else:
                boundary_messages.append(
                    f"{version}의 0.5 경계 평면은 그림 범위 밖에 있습니다."
                )
        else:
            boundary_messages.append(
                f"{version}의 경계 평면은 현재 축 조합에서 표시할 수 없습니다."
            )

    fig.update_layout(
        scene=dict(
            xaxis_title=x_label,
            yaxis_title=y_label,
            zaxis_title=z_label,
        ),
        height=760,
        legend_title="범례",
    )

    st.plotly_chart(fig, use_container_width=True)

    for message in boundary_messages:
        st.warning(message)


# ==================================================
# 8. 로지스틱 회귀가 놓친 환자 목록
# ==================================================
st.subheader("4. 로지스틱 회귀가 놓친 환자")

list_version = "적용 후" if balance_switch else "적용 전"
list_prediction = predictions["로지스틱 회귀"][list_version]

missed_df = test_df.copy()
missed_df["실제"] = y_test.to_numpy()
missed_df["예측"] = list_prediction

missed_df = missed_df[
    (missed_df["실제"] == 1) &
    (missed_df["예측"] == 0)
].sort_values("age", ascending=True)

st.markdown(
    f"**{list_version} 놓친 환자: {len(missed_df):,}명**"
)

st.caption(
    "실제로 뇌졸중을 겪었지만 로지스틱 회귀가 뇌졸중이 아니라고 예측한 사람입니다. "
    "나이가 적은 순서로 표시합니다."
)

missed_display = pd.DataFrame({
    "번호": range(1, len(missed_df) + 1),
    "나이": missed_df["age"].to_numpy(),
    "고혈압 여부": missed_df["hypertension"].map(
        {0: "아니요", 1: "예"}
    ).to_numpy(),
    "심장병 여부": missed_df["heart_disease"].map(
        {0: "아니요", 1: "예"}
    ).to_numpy(),
})

if missed_display.empty:
    st.success("놓친 환자가 없습니다.")
else:
    st.dataframe(
        missed_display.head(20),
        hide_index=True,
        use_container_width=True,
    )

    if len(missed_display) > 20:
        st.caption(
            f"전체 {len(missed_display):,}명 중 나이가 적은 순서로 "
            "앞의 20명만 표시했습니다."
        )

st.caption(
    f"목록 인원수 {len(missed_df):,}명 = "
    f"로지스틱 회귀 혼동행렬의 {list_version} FN "
    f"{results['로지스틱 회귀'][list_version]['cm']['FN']:,}명"
)
