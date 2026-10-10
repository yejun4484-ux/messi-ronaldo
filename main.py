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
st.caption("함께 먹는 메뉴의 패턴을 찾아보는 장바구니 분석")


# --------------------------------------------------
# 데이터 불러오기
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

    # 메뉴 이름의 괄호와 그 안의 내용 제거
    # 예: 돈가스(소스 포함) -> 돈가스
    # 괄호가 여러 개 있어도 반복해서 제거
    def clean_menu(name):
        name = str(name).strip()

        previous = None
        while previous != name:
            previous = name
            name = re.sub(r"\([^()]*\)", "", name)
            name = re.sub(r"\[[^\[\]]*\]", "", name)
            name = re.sub(r"（[^（）]*）", "", name)

        return re.sub(r"\s+", " ", name).strip()

    baskets = []

    for menu_text in df["메뉴"]:
        items = {
            clean_menu(item)
            for item in menu_text.split("|")
            if clean_menu(item)
        }
        baskets.append(items)

    df["장바구니"] = baskets

    # 메뉴가 하나도 없는 식단은 분석에서 제외
    df = df[df["장바구니"].map(len) > 0].reset_index(drop=True)

    return df


# --------------------------------------------------
# 연관 규칙 계산
# --------------------------------------------------
@st.cache_data
def make_rules(baskets):
    total_days = len(baskets)

    if total_days == 0:
        return pd.DataFrame(), 0, 0

    # 각 메뉴가 등장한 식단 수
    menu_count = {}
    # 두 메뉴가 함께 등장한 식단 수
    pair_count = {}

    for basket in baskets:
        for menu in basket:
            menu_count[menu] = menu_count.get(menu, 0) + 1

        for a, b in combinations(sorted(basket), 2):
            pair_count[(a, b)] = pair_count.get((a, b), 0) + 1

    menu_types = len(menu_count)
    pair_types = len(pair_count)

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

    rules = pd.DataFrame(
        rows,
        columns=["조건", "결과", "동시", "지지도", "신뢰도", "향상도"],
    )

    return rules, menu_types, pair_types


# --------------------------------------------------
# 앱 실행
# --------------------------------------------------
try:
    df = load_data()
except Exception as e:
    st.error(f"데이터를 불러오지 못했습니다: {e}")
    st.info("CSV 주소와 인터넷 연결, 열 이름을 확인해 주세요.")
    st.stop()


baskets = df["장바구니"].tolist()
rules, menu_types, pair_types = make_rules(baskets)

if not rules.empty:
    # 실제 메뉴 목록
    all_menus = sorted(
        {menu for basket in baskets for menu in basket}
    )

    # 상단 요약
    c1, c2, c3 = st.columns(3)
    c1.metric("급식 일수", f"{len(baskets):,}일")
    c2.metric("메뉴 종류 수", f"{menu_types:,}종")
    c3.metric("함께 나온 메뉴 쌍의 수", f"{pair_types:,}쌍")

    st.divider()

    # --------------------------------------------------
    # 필터 및 정렬
    # --------------------------------------------------
    st.subheader("🔎 연관 규칙 탐색")

    col1, col2 = st.columns(2)

    with col1:
        selected_menu = st.selectbox(
            "메뉴 선택",
            options=["전체 메뉴"] + all_menus,
            index=0,
        )

    with col2:
        sort_option = st.selectbox(
            "정렬 기준",
            options=["향상도 순", "신뢰도 순", "동시 순"],
            index=0,
        )

    filtered = rules.copy()

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

    st.caption(
        "지지도 = 두 메뉴가 함께 나온 비율 · "
        "신뢰도 = 조건 메뉴가 나왔을 때 결과 메뉴도 나온 비율 · "
        "향상도 = 결과 메뉴의 평소 등장 비율 대비 실제 등장 비율"
    )

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

    st.caption(f"현재 표시 중인 규칙: {len(filtered):,}개")

    # --------------------------------------------------
    # 향상도 상위 10개 막대그래프
    # --------------------------------------------------
    st.divider()
    st.subheader("📊 향상도 상위 10개 규칙")

    if filtered.empty:
        st.info("선택한 메뉴와 관련된 규칙이 없습니다.")
    else:
        top10 = (
            filtered.sort_values(
                "향상도", ascending=False, kind="stable"
            )
            .head(10)
            .copy()
        )

        # 조건 -> 결과 형식으로 라벨 생성
        top10["규칙"] = top10["조건"] + " → " + top10["결과"]

        # 가장 높은 값이 위에 표시되도록 순서 지정
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
            title="함께 등장할 가능성이 평소보다 높은 규칙",
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

        st.markdown(
            """
            **향상도 해석**
            - **1보다 큼:** 두 메뉴가 우연히 독립적으로 등장한다고 볼 때보다 자주 함께 나옴
            - **1과 같음:** 두 메뉴의 등장 사이에 특별한 연관이 관찰되지 않음
            - **1보다 작음:** 두 메뉴가 함께 나오는 경향이 상대적으로 적음

            향상도가 높더라도 함께 나온 횟수가 매우 적을 수 있으므로,
            지지도와 신뢰도도 같이 확인하는 것이 좋아요.
            """
        )

else:
    st.warning(
        "분석할 메뉴 쌍이 없습니다. 메뉴 데이터와 구분 기호(|)를 확인해 주세요."
    )

# --------------------------------------------------
# 원본 데이터 확인
# --------------------------------------------------
with st.expander("원본 데이터와 전처리 결과 보기"):
    raw_view = df[["날짜", "식사", "메뉴"]].copy()
    st.dataframe(raw_view, use_container_width=True, hide_index=True)

    st.caption(
        "분석에서는 메뉴명의 괄호 내용을 제거하고, "
        "같은 식단 안의 중복 메뉴는 한 번만 계산합니다."
    )
