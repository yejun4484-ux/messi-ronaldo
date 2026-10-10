
import streamlit as st
import pandas as pd

from pathlib import Path

# -----------------------------
# 페이지 설정
# -----------------------------
st.set_page_config(
    page_title="뇌졸중 예측 실습실",
    page_icon="🧠",
    layout="wide",
)

# -----------------------------
# 페이지 메뉴 설정
# -----------------------------
BASE_DIR = Path(__file__).parent

home_page = st.Page(
    str(BASE_DIR / "main.py"),
    title="홈",
    icon="🏠",
    default=True,
)

explore_page = st.Page(
    str(BASE_DIR / "PAGES" / "1_탐색.py"),
    title="탐색",
    icon="🔎",
)

# 왼쪽 사이드바에 페이지 메뉴 표시
navigation = st.navigation({
    "뇌졸중 예측 실습실": [
        home_page,
        explore_page,
    ]
})

# 선택한 페이지 실행
navigation.run()

# -----------------------------
# 데이터 불러오기
# -----------------------------
DATA_URL = (
    "https://raw.githubusercontent.com/"
    "greatsong/modudata/main/data/stroke.csv"
)


@st.cache_data
def load_data():
    return pd.read_csv(DATA_URL, encoding="utf-8")


st.title("🧠 뇌졸중 예측 실습실")
st.subheader("데이터를 살펴보며 예측 실습을 준비해 봅시다")

st.write(
    "이 데이터는 사람들의 기본 정보와 건강 관련 정보, "
    "생활 습관, 그리고 뇌졸중 발생 여부를 담고 있습니다. "
    "먼저 데이터의 크기와 각 열의 특징, 비어 있는 값이 있는지 확인합니다."
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

# -----------------------------
# 요약 숫자 카드
# -----------------------------
total_people = len(df)
column_count = len(df.columns)

stroke_count = int(
    (pd.to_numeric(df["stroke"], errors="coerce") == 1).sum()
)

stroke_rate = (
    stroke_count / total_people * 100
    if total_people > 0
    else 0
)

st.markdown("### 데이터 한눈에 보기")

c1, c2, c3, c4 = st.columns(4)

c1.metric("전체 사람 수", f"{total_people:,}명")
c2.metric("열 개수", f"{column_count:,}개")
c3.metric("stroke가 1인 사람 수", f"{stroke_count:,}명")
c4.metric("stroke가 1인 비율", f"{stroke_rate:.2f}%")

st.caption(
    "비율은 전체 행 중 stroke 값이 1인 행의 비율입니다. "
    "이 데이터만으로 개인의 뇌졸중 위험을 판단할 수는 없습니다."
)

# -----------------------------
# 열 정보 표
# -----------------------------
st.markdown("### 열 정보")
st.write(
    "우리말 뜻 칸을 클릭해 교재를 참고하여 직접 입력해 보세요."
)

binary_columns = {
    "hypertension",
    "heart_disease",
    "stroke",
}

categorical_columns = {
    "gender",
    "ever_married",
    "work_type",
    "Residence_type",
    "smoking_status",
}


def value_kind(column, series):
    if column in binary_columns:
        return "0 또는 1"

    if column in categorical_columns:
        values = sorted(
            series.dropna().astype(str).unique().tolist()
        )
        if len(values) > 5:
            return f"문자형 범주 ({len(values)}종류)"
        return (
            "문자형: " + ", ".join(values)
            if values
            else "문자형"
        )

    if pd.api.types.is_numeric_dtype(series):
        return "숫자형"

    values = sorted(
        series.dropna().astype(str).unique().tolist()
    )
    return f"문자형 범주 ({len(values)}종류)"


column_info = pd.DataFrame({
    "열 이름": df.columns.tolist(),
    "우리말 뜻": ["" for _ in df.columns],
    "값의 종류": [
        value_kind(col, df[col])
        for col in df.columns
    ],
    "빈 값 개수": [
        int(df[col].isna().sum())
        for col in df.columns
    ],
})

st.data_editor(
    column_info,
    use_container_width=True,
    hide_index=True,
    num_rows="fixed",
    key="column_info_editor",
    column_config={
        "열 이름": st.column_config.TextColumn(
            "열 이름",
            disabled=True,
        ),
        "우리말 뜻": st.column_config.TextColumn(
            "우리말 뜻",
            help="이 칸을 클릭해 우리말 뜻을 입력하세요.",
        ),
        "값의 종류": st.column_config.TextColumn(
            "값의 종류",
            disabled=True,
        ),
        "빈 값 개수": st.column_config.NumberColumn(
            "빈 값 개수",
            format="%d",
            disabled=True,
        ),
    },
)

# -----------------------------
# 원본 데이터 첫 5행
# -----------------------------
st.markdown("### 데이터 첫 5행")

st.dataframe(
    df.head(5),
    use_container_width=True,
    hide_index=True,
)

# -----------------------------
# 데이터 출처
# -----------------------------
st.markdown("### 데이터 출처")

st.text_area(
    "데이터 출처",
    placeholder="교재에 나온 데이터 출처를 입력하세요.",
    height=100,
)

st.divider()

st.caption(
    "이 앱은 데이터 탐색을 위한 교육용 예제입니다. "
    "실제 의료 진단에 사용하지 마세요."
)
