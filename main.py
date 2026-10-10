
import re
from itertools import combinations

import pandas as pd
import plotly.express as px
import streamlit as st


# --------------------------------------------------
# 페이지 설정
# --------------------------------------------------
st.set_page_config(
    page_title="급식 규칙 찾기",
    page_icon="🍱",
    layout="wide",
)

DATA_URL = (
    "https://raw.githubusercontent.com/teacher188-netizen/"
    "2026-datascience/refs/heads/main/dorim_meals.csv"
)

st.title("🍱 급식 규칙 찾기")
st.caption("함께 나오는 메뉴와 한 번도 함께 나오지 않은 메뉴를 찾아봅니다.")


# --------------------------------------------------
# 데이터 불러오기 및 전처리
# --------------------------------------------------
@st.cache_data
def load_data():
    df = pd.read_csv(DATA_URL, encoding="utf-8")

    required_columns = {"날짜", "식사", "메뉴"}
    missing = required_columns - set(df.columns)

    if missing:
        raise ValueError(
            f"CSV에 필요한 열이 없습니다: {', '.join(sorted(missing))}"
        )

    df = df[["날짜", "식사", "메뉴"]].copy()
    df = df.dropna(subset=["메뉴"])
    df["메뉴"] = df["메뉴"].astype(str)

    def clean_menu(name):
        name = str(name).strip()

        # 괄호 안의 내용을 반복적으로 제거
        previous = None
        while previous != name:
            previous = name
            name = re.sub(r"\([^()]*\)", "", name)
            name = re.sub(r"\[[^\[\]]*\]", "", name)
            name = re.sub(r"（[^（）]*）", "", name)

        return re.sub(r"\s+", " ", name).strip()

    baskets = []

    for menu_text in df["메뉴"]:
        items = set()

        for item in menu_text.split("|"):
            cleaned = clean_menu(item)
            if cleaned:
                items.add(cleaned)

        baskets.append(items)

    df["장바구니"] = baskets

    # 메뉴가 하나도 없는 식단은 제외
    df = df[df["장바구니"].map(len) > 0].reset_index(drop=True)

    return df


# --------------------------------------------------
# 연관 규칙 계산
# --------------------------------------------------
@st.cache_data
def make_rules(baskets):
    total_days = len(baskets)

    menu_count = {}
    pair_count = {}

    for basket in baskets:
        for menu in basket:
            menu_count[menu] = menu_count.get(menu, 0) + 1

        for a, b in combinations(sorted(basket), 2):
            pair_count[(a, b)] = pair_count.get((a, b), 0) + 1

    columns = [
        "조건", "결과", "동시", "지지도", "신뢰도", "향상도"
    ]

    rows = []

    for (a, b), both_count in pair_count.items():
        support = both_count / total_days

        # A -> B
        confidence_ab = both_count / menu_count[a]
        lift_ab = confidence_ab / (menu_count[b] / total_days)

        rows.append({
            "조건": a,
            "결과": b,
            "동시": both_count,
            "지지도": support,
            "신뢰도": confidence_ab,
            "향상도": lift_ab,
        })

        # B -> A
        confidence_ba = both_count / menu_count[b]
        lift_ba = confidence_ba / (menu_count[a] / total_days)

        rows.append({
            "조건": b,
            "결과": a,
            "동시": both_count,
            "지지도": support,
            "신뢰도": confidence_ba,
            "향상도": lift_ba,
        })

    rules = pd.DataFrame(rows, columns=columns)

    return rules, menu_count, pair_count


# --------------------------------------------------
# 앱 실행
# --------------------------------------------------
try:
    df = load_data()
except Exception as e:
    st.error(f"데이터를 불러오지 못했습니다: {e}")
    st.info("CSV 주소, 인터넷 연결, 열 이름을 확인해 주세요.")
    st.stop()


baskets = df["장바구니"].tolist()
total_days = len(baskets)

rules, menu_count, pair_count = make_rules(baskets)

all_menus = sorted(menu_count.keys())
menu_types = len(all_menus)
pair_types = len(pair_count)


# --------------------------------------------------
# 상단 요약
# --------------------------------------------------
c1, c2, c3 = st.columns(3)

c1.metric("급식 일수", f"{total_days:,}일")
c2.metric("메뉴 종류 수", f"{menu_types:,}종")
c3.metric("함께 나온 메뉴 쌍의 수", f"{pair_types:,}쌍")

st.divider()


# --------------------------------------------------
# 연관 규칙 탐색
# --------------------------------------------------
st.subheader("🔎 연관 규칙 탐색")

col1, col2 = st.columns(2)

with col1:
    selected_menu = st.selectbox(
        "좁혀 보기: 메뉴 선택",
        options=["전체 메뉴"] + all_menus,
        index=0,
        key="rule_menu_filter",
    )

with col2:
    sort_option = st.selectbox(
        "정렬 기준",
        options=["향상도 순", "신뢰도 순", "동시 순"],
        index=0,
        key="rule_sort",
    )

min_cooccurrence = st.slider(
    "최소 동시 일수",
    min_value=1,
    max_value=10,
    value=1,
    step=1,
    help="선택한 일수보다 적게 함께 나온 규칙은 표와 그래프에서 제외합니다.",
)

# 최소 동시 일수 적용
filtered = rules[rules["동시"] >= min_cooccurrence].copy()

# 선택 메뉴가 조건 또는 결과에 포함된 규칙만 남김
if selected_menu != "전체 메뉴":
    filtered = filtered[
        (filtered["조건"] == selected_menu)
        | (filtered["결과"] == selected_menu)
    ].copy()

sort_columns = {
    "향상도 순": "향상도",
    "신뢰도 순": "신뢰도",
    "동시 순": "동시",
}

filtered = filtered.sort_values(
    sort_columns[sort_option],
    ascending=False,
    kind="stable",
).reset_index(drop=True)


# --------------------------------------------------
# 규칙 표
# --------------------------------------------------
st.subheader("📋 연관 규칙 표")

# 슬라이더와 메뉴 필터 적용 후 남은 규칙 수
st.write(f"**현재 표에 남은 규칙: {len(filtered):,}개**")

st.caption(
    "지지도 = 두 메뉴가 함께 나온 비율 · "
    "신뢰도 = 조건 메뉴가 나온 날 중 결과 메뉴도 나온 비율 · "
    "향상도 = 결과 메뉴의 평소 등장 비율 대비 실제 등장 비율"
)

if filtered.empty:
    st.info(
        "현재 조건에 맞는 규칙이 없습니다. "
        "최소 동시 일수를 낮추거나 다른 메뉴를 선택해 보세요."
    )
else:
    display_rules = filtered.copy()

    display_rules["지지도"] = display_rules["지지도"].map(
        lambda x: f"{x:.1%}"
    )
    display_rules["신뢰도"] = display_rules["신뢰도"].map(
        lambda x: f"{x:.1%}"
    )
    display_rules["향상도"] = display_rules["향상도"].map(
        lambda x: f"{x:.3f}"
    )

    st.dataframe(
        display_rules,
        use_container_width=True,
        hide_index=True,
        height=420,
    )

st.caption(
    "같은 메뉴 쌍은 조건과 결과를 바꾼 두 방향의 규칙으로 표시됩니다."
)


# --------------------------------------------------
# 향상도 상위 10개 그래프
# --------------------------------------------------
st.divider()
st.subheader("📊 향상도 상위 10개 규칙")

if filtered.empty:
    st.info("그래프로 표시할 규칙이 없습니다.")
else:
    top10 = (
        filtered.sort_values(
            "향상도",
            ascending=False,
            kind="stable",
        )
        .head(10)
        .copy()
    )

    top10["규칙"] = top10["조건"] + " → " + top10["결과"]

    # 가로 막대그래프에서 가장 높은 값이 위에 표시되도록 정렬
    top10 = top10.sort_values("향상도", ascending=True)

    fig = px.bar(
        top10,
        x="향상도",
        y="규칙",
        orientation="h",
        text="향상도",
        hover_data={
            "동시": True,
            "지지도": ":.1%",
            "신뢰도": ":.1%",
            "향상도": ":.3f",
            "규칙": False,
        },
        labels={
            "향상도": "향상도",
            "규칙": "연관 규칙",
            "동시": "함께 나온 일수",
        },
        title="향상도가 높은 규칙",
    )

    fig.update_traces(
        texttemplate="%{text:.2f}",
        textposition="outside",
        cliponaxis=False,
    )

    fig.update_layout(
        yaxis_title="",
        xaxis_title="향상도",
        height=max(380, len(top10) * 42),
        margin=dict(l=20, r=70, t=60, b=40),
    )

    st.plotly_chart(fig, use_container_width=True)

st.caption(
    "향상도가 1보다 크면 두 메뉴가 독립적으로 등장한다고 예상할 때보다 "
    "자주 함께 나온다는 뜻입니다. 함께 나온 횟수와 신뢰도도 같이 확인하세요."
)


# --------------------------------------------------
# 함께 나온 적 없는 짝
# --------------------------------------------------
st.divider()
st.subheader("🚫 함께 나온 적 없는 짝")

st.write(
    "메뉴 하나를 선택하면, 그 메뉴와 같은 날 한 번도 함께 나오지 않았지만 "
    "자신은 10일 이상 등장한 메뉴를 찾아줍니다."
)

selected_absent_menu = st.selectbox(
    "함께 나온 적 없는 짝 찾기: 기준 메뉴 선택",
    options=all_menus,
    index=0,
    key="absent_menu_filter",
)

# 기준 메뉴가 나온 날짜 수
selected_days = menu_count[selected_absent_menu]

st.metric(
    f"'{selected_absent_menu}' 등장 일수",
    f"{selected_days:,}일",
)

# 기준 메뉴와 함께 나온 적이 있는 메뉴 집합
cooccurred_menus = set()

for basket in baskets:
    if selected_absent_menu in basket:
        cooccurred_menus.update(basket)

# 자기 자신 제외, 함께 나온 적 없는 메뉴 중 10일 이상 등장한 메뉴
absent_candidates = [
    (menu, days)
    for menu, days in menu_count.items()
    if menu != selected_absent_menu
    and menu not in cooccurred_menus
    and days >= 10
]

absent_df = pd.DataFrame(
    absent_candidates,
    columns=["메뉴", "등장 일수"],
)

if absent_df.empty:
    st.info(
        "이 메뉴와 한 번도 함께 나오지 않았고 "
        "10일 이상 등장한 메뉴가 없습니다."
    )
else:
    absent_df = absent_df.sort_values(
        "등장 일수",
        ascending=False,
        kind="stable",
    ).reset_index(drop=True)

    st.write(
        f"**조건에 맞는 메뉴: {len(absent_df):,}종**"
    )

    st.dataframe(
        absent_df,
        use_container_width=True,
        hide_index=True,
    )

    st.caption(
        "등장 일수는 해당 메뉴가 포함된 급식 일수입니다. "
        "같은 식단에 같은 메뉴가 중복 기재되어 있어도 하루에 한 번만 셉니다."
    )


# --------------------------------------------------
# 원본 데이터 확인
# --------------------------------------------------
with st.expander("원본 데이터 보기"):
    st.dataframe(
        df[["날짜", "식사", "메뉴"]],
        use_container_width=True,
        hide_index=True,
    )

    st.caption(
        "분석 전 메뉴명의 괄호 내용은 제거됩니다. "
        "한 식단 안에서 같은 메뉴는 한 번만 계산합니다."
    )
