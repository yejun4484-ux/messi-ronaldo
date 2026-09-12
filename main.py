import streamlit as st
import requests
import pandas as pd
import re
from collections import Counter

# ==========================================
# 기본 설정
# ==========================================

st.set_page_config(
    page_title="학교 3곳 급식 비교",
    page_icon="🍚",
    layout="wide"
)

st.title("🍚 학교 3곳 급식 비교 분석")
st.write(
    "나이스 교육정보 개방 포털의 급식 데이터를 이용하여 "
    "3개 학교의 급식 다양성과 메뉴 조합을 비교합니다."
)

BASE_URL = "https://open.neis.go.kr/hub"

# ==========================================
# API KEY
# ==========================================

try:
    API_KEY = st.secrets["NEIS_API_KEY"]
except Exception:
    st.error(
        "NEIS API 키가 설정되지 않았습니다. "
        "Streamlit Secrets에 NEIS_API_KEY를 추가해주세요."
    )
    st.stop()


# ==========================================
# 학교 검색
# ==========================================

def search_school(school_name):

    url = f"{BASE_URL}/schoolInfo"

    params = {
        "KEY": API_KEY,
        "Type": "json",
        "pSize": 1000,
        "SCHUL_NM": school_name
    }

    try:

        response = requests.get(
            url,
            params=params,
            timeout=10
        )

        response.raise_for_status()

        data = response.json()

        if "schoolInfo" in data:

            return data["schoolInfo"][1]["row"]

        return []

    except Exception as e:

        st.error(
            f"학교 검색 중 오류가 발생했습니다: {e}"
        )

        return []


# ==========================================
# 급식 데이터 가져오기
# ==========================================

def get_meal_data(
    atpt_code,
    school_code,
    start_date,
    end_date
):

    url = f"{BASE_URL}/mealServiceDietInfo"

    params = {
        "KEY": API_KEY,
        "Type": "json",

        "ATPT_OFCDC_SC_CODE": atpt_code,

        "SD_SCHUL_CODE": school_code,

        "MMEAL_SC_CODE": "2",

        "MLSV_FROM_YMD": start_date,

        "MLSV_TO_YMD": end_date,

        "pSize": 1000,

        "pIndex": 1
    }

    try:

        response = requests.get(
            url,
            params=params,
            timeout=10
        )

        response.raise_for_status()

        data = response.json()

        # 정상적인 급식 데이터
        if "mealServiceDietInfo" in data:

            return data["mealServiceDietInfo"][1]["row"]

        # 데이터 없음
        if "RESULT" in data:

            result = data["RESULT"]

            if result.get("CODE") == "INFO-200":

                return []

            st.error(
                f"나이스 API 오류: "
                f"{result.get('CODE')} - "
                f"{result.get('MESSAGE')}"
            )

            return []

        return []

    except Exception as e:

        st.error(
            f"급식 데이터를 가져오는 중 오류가 발생했습니다: {e}"
        )

        return []


# ==========================================
# 메뉴 이름 정리
# ==========================================

def clean_menu(menu):

    # 알레르기 번호 제거
    menu = re.sub(
        r"\([^)]*\)",
        "",
        menu
    )

    # 숫자 제거
    menu = re.sub(
        r"\d+",
        "",
        menu
    )

    # 별표 제거
    menu = menu.replace(
        "*",
        ""
    )

    # 여러 공백을 하나로
    menu = re.sub(
        r"\s+",
        " ",
        menu
    )

    return menu.strip()


# ==========================================
# 급식 메뉴 분리
# ==========================================

def split_menus(menu_text):

    menus = re.split(
        r"<br\s*/?>",
        str(menu_text)
    )

    result = []

    for menu in menus:

        menu = clean_menu(menu)

        if menu:

            result.append(menu)

    return result


# ==========================================
# 학교 급식 분석
# ==========================================

def analyze_school(
    school,
    start_date,
    end_date
):

    meals = get_meal_data(
        school["ATPT_OFCDC_SC_CODE"],
        school["SD_SCHUL_CODE"],
        start_date.strftime("%Y%m%d"),
        end_date.strftime("%Y%m%d")
    )

    if not meals:

        return None

    df = pd.DataFrame(meals)

    # 필요한 데이터가 있는지 확인
    required_columns = [
        "MLSV_YMD",
        "DDISH_NM",
        "CAL_INFO"
    ]

    for column in required_columns:

        if column not in df.columns:

            return None

    df = df[required_columns]

    df.columns = [
        "날짜",
        "메뉴",
        "칼로리"
    ]

    # 날짜 변환
    df["날짜"] = pd.to_datetime(
        df["날짜"],
        format="%Y%m%d"
    )

    # 메뉴 분리
    df["메뉴목록"] = df["메뉴"].apply(
        split_menus
    )

    # 전체 메뉴
    all_menus = []

    for menus in df["메뉴목록"]:

        all_menus.extend(menus)

    # 메뉴별 등장 횟수
    menu_count = Counter(
        all_menus
    )

    menu_df = pd.DataFrame(
        menu_count.items(),
        columns=[
            "메뉴",
            "등장횟수"
        ]
    )

    menu_df = menu_df.sort_values(
        "등장횟수",
        ascending=False
    )

    # ==========================================
    # 칼로리 계산
    # ==========================================

    calories = []

    for value in df["칼로리"]:

        match = re.search(
            r"\d+(\.\d+)?",
            str(value)
        )

        if match:

            calories.append(
                float(match.group())
            )

    if calories:

        average_calorie = (
            sum(calories) /
            len(calories)
        )

    else:

        average_calorie = 0

    # ==========================================
    # 다양성 점수
    # ==========================================

    total_menu_count = len(
        all_menus
    )

    unique_menu_count = len(
        set(all_menus)
    )

    if total_menu_count > 0:

        diversity_score = (
            unique_menu_count /
            total_menu_count
        ) * 100

    else:

        diversity_score = 0

    return {

        "학교명":
            school["SCHUL_NM"],

        "급식일수":
            len(df),

        "전체메뉴수":
            total_menu_count,

        "서로다른메뉴":
            unique_menu_count,

        "다양성점수":
            round(
                diversity_score,
                1
            ),

        "평균칼로리":
            round(
                average_calorie,
                1
            ),

        "메뉴분석":
            menu_df,

        "원본데이터":
            df
    }


# ==========================================
# 특정 메뉴와 함께 나온 메뉴 TOP 3
# ==========================================

def find_related_top3(
    result,
    target_menu
):

    df = result["원본데이터"]

    target_menu = clean_menu(
        target_menu
    )

    related_menus = []

    # ==========================================
    # 해당 메인 메뉴가 나온 날 찾기
    # ==========================================

    for menus in df["메뉴목록"]:

        # 메인 메뉴가 포함된 날인지 확인
        has_target = any(
            target_menu in menu
            for menu in menus
        )

        if not has_target:

            continue

        # ======================================
        # 같은 날 나온 다른 메뉴 수집
        # ======================================

        for menu in menus:

            # 메인 메뉴 자체는 제외
            if target_menu in menu:

                continue

            related_menus.append(
                menu
            )

    # ==========================================
    # 함께 나온 메뉴 횟수 계산
    # ==========================================

    counter = Counter(
        related_menus
    )

    if not counter:

        return pd.DataFrame(
            columns=[
                "순위",
                "함께 나온 메뉴",
                "횟수"
            ]
        )

    top3 = counter.most_common(3)

    top3_df = pd.DataFrame(
        top3,
        columns=[
            "함께 나온 메뉴",
            "횟수"
        ]
    )

    top3_df.insert(
        0,
        "순위",
        range(
            1,
            len(top3_df) + 1
        )
    )

    return top3_df


# ==========================================
# 사이드바
# ==========================================

st.sidebar.header(
    "⚙️ 비교 설정"
)

st.sidebar.write(
    "비교할 학교 3곳을 입력하세요."
)

school_names = []

for i in range(3):

    name = st.sidebar.text_input(
        f"{i + 1}번째 학교",
        placeholder="예: 인천고등학교",
        key=f"school_{i}"
    )

    school_names.append(
        name
    )


# ==========================================
# 메인 메뉴 설정
# ==========================================

st.sidebar.markdown("---")

target_menu = st.sidebar.text_input(
    "🍖 분석할 메인 메뉴",
    placeholder="예: 제육볶음"
)

st.sidebar.caption(
    "입력한 메뉴가 나온 날에 "
    "함께 나온 메뉴 TOP 3를 학교별로 분석합니다."
)


# ==========================================
# 날짜 설정
# ==========================================

start_date = st.sidebar.date_input(
    "시작 날짜",
    pd.Timestamp("2026-03-01")
)

end_date = st.sidebar.date_input(
    "끝 날짜",
    pd.Timestamp("2026-07-31")
)


# ==========================================
# 학교 검색
# ==========================================

if st.sidebar.button(
    "🔎 3개 학교 검색"
):

    st.session_state[
        "school_results"
    ] = {}

    for i, name in enumerate(
        school_names
    ):

        if not name:

            continue

        with st.spinner(
            f"{name} 검색 중..."
        ):

            results = search_school(
                name
            )

        st.session_state[
            "school_results"
        ][i] = results


# ==========================================
# 학교 선택
# ==========================================

selected_schools = []

if "school_results" in st.session_state:

    st.subheader(
        "🏫 학교 선택"
    )

    for i in range(3):

        results = st.session_state[
            "school_results"
        ].get(i, [])

        if not results:

            st.warning(
                f"{i + 1}번째 학교를 찾지 못했습니다."
            )

            continue

        options = [
            f"{school['SCHUL_NM']} "
            f"({school['LCTN_SC_NM']})"
            for school in results
        ]

        selected = st.selectbox(
            f"{i + 1}번째 학교 선택",
            options,
            key=f"selected_{i}"
        )

        index = options.index(
            selected
        )

        selected_schools.append(
            results[index]
        )


# ==========================================
# 분석 시작
# ==========================================

if len(selected_schools) == 3:

    if st.button(
        "🍚 3개 학교 비교 분석 시작"
    ):

        if start_date > end_date:

            st.error(
                "시작 날짜가 끝 날짜보다 늦습니다."
            )

        else:

            results = []

            progress = st.progress(
                0
            )

            for i, school in enumerate(
                selected_schools
            ):

                with st.spinner(
                    f"{school['SCHUL_NM']} "
                    "급식 데이터 분석 중..."
                ):

                    result = analyze_school(
                        school,
                        start_date,
                        end_date
                    )

                if result:

                    results.append(
                        result
                    )

                progress.progress(
                    (i + 1) / 3
                )

            # ======================================
            # 데이터 확인
            # ======================================

            if len(results) < 3:

                st.error(
                    "3개 학교의 급식 데이터를 "
                    "모두 가져오지 못했습니다."
                )

            else:

                # ==================================
                # 학교 비교표
                # ==================================

                st.subheader(
                    "📊 학교별 급식 비교"
                )

                comparison = pd.DataFrame({

                    "학교": [
                        r["학교명"]
                        for r in results
                    ],

                    "급식일수": [
                        r["급식일수"]
                        for r in results
                    ],

                    "전체 메뉴 수": [
                        r["전체메뉴수"]
                        for r in results
                    ],

                    "서로 다른 메뉴": [
                        r["서로다른메뉴"]
                        for r in results
                    ],

                    "다양성 점수": [
                        r["다양성점수"]
                        for r in results
                    ],

                    "평균 칼로리": [
                        r["평균칼로리"]
                        for r in results
                    ]
                })

                st.dataframe(
                    comparison,
                    use_container_width=True,
                    hide_index=True
                )


                # ==================================
                # 다양성 그래프
                # ==================================

                st.subheader(
                    "🌱 급식 다양성 비교"
                )

                diversity_chart = comparison[
                    [
                        "학교",
                        "다양성 점수"
                    ]
                ].set_index(
                    "학교"
                )

                st.bar_chart(
                    diversity_chart
                )


                # ==================================
                # 칼로리 그래프
                # ==================================

                st.subheader(
                    "🔥 평균 칼로리 비교"
                )

                calorie_chart = comparison[
                    [
                        "학교",
                        "평균 칼로리"
                    ]
                ].set_index(
                    "학교"
                )

                st.bar_chart(
                    calorie_chart
                )


                # ==================================
                # 다양성 순위
                # ==================================

                st.subheader(
                    "🏆 급식 다양성 순위"
                )

                ranking = comparison.sort_values(
                    "다양성 점수",
                    ascending=False
                ).reset_index(
                    drop=True
                )

                ranking.insert(
                    0,
                    "순위",
                    range(
                        1,
                        len(ranking) + 1
                    )
                )

                st.dataframe(
                    ranking[
                        [
                            "순위",
                            "학교",
                            "다양성 점수"
                        ]
                    ],
                    use_container_width=True,
                    hide_index=True
                )


                # ==================================
                # 메인 메뉴 조합 분석
                # ==================================

                if target_menu:

                    st.markdown("---")

                    st.subheader(
                        f"🍖 '{target_menu}'와 "
                        "함께 나온 메뉴 TOP 3"
                    )

                    st.write(
                        f"'{target_menu}'가 나온 날에 "
                        "함께 제공된 메뉴를 분석합니다."
                    )

                    related_results = []

                    for result in results:

                        top3 = find_related_top3(
                            result,
                            target_menu
                        )

                        related_results.append(
                            (
                                result["학교명"],
                                top3
                            )
                        )


                    # ==================================
                    # 학교 3곳 TOP 3
                    # ==================================

                    cols = st.columns(
                        3
                    )

                    for i, (
                        school_name,
                        top3
                    ) in enumerate(
                        related_results
                    ):

                        with cols[i]:

                            st.markdown(
                                f"### 🏫 {school_name}"
                            )

                            if top3.empty:

                                st.info(
                                    f"'{target_menu}'가 "
                                    "나온 날이 없습니다."
                                )

                            else:

                                st.dataframe(
                                    top3,
                                    use_container_width=True,
                                    hide_index=True
                                )


                    # ==================================
                    # 학교별 1위 비교
                    # ==================================

                    st.subheader(
                        f"🥇 '{target_menu}' "
                        "최다 조합 비교"
                    )

                    first_menus = []

                    for (
                        school_name,
                        top3
                    ) in related_results:

                        if not top3.empty:

                            first = top3.iloc[0]

                            first_menus.append({

                                "학교":
                                    school_name,

                                "가장 많이 함께 나온 메뉴":
                                    first["함께 나온 메뉴"],

                                "횟수":
                                    first["횟수"]
                            })

                    if first_menus:

                        first_df = pd.DataFrame(
                            first_menus
                        )

                        st.dataframe(
                            first_df,
                            use_container_width=True,
                            hide_index=True
                        )


                    # ==================================
                    # 분석 문장
                    # ==================================

                    st.subheader(
                        "💡 메뉴 조합 분석"
                    )

                    for (
                        school_name,
                        top3
                    ) in related_results:

                        if not top3.empty:

                            first = top3.iloc[0]

                            st.write(
                                f"**{school_name}**에서는 "
                                f"'{target_menu}'가 나온 날 "
                                f"**{first['함께 나온 메뉴']}**가 "
                                f"가장 많이 함께 나왔습니다 "
                                f"({first['횟수']}회)."
                            )


                # ==================================
                # 학교별 반복 메뉴
                # ==================================

                st.markdown("---")

                st.subheader(
                    "🔁 학교별 많이 나온 메뉴"
                )

                cols = st.columns(
                    3
                )

                for i, result in enumerate(
                    results
                ):

                    with cols[i]:

                        st.markdown(
                            f"### {result['학교명']}"
                        )

                        st.dataframe(
                            result["메뉴분석"].head(10),
                            use_container_width=True,
                            hide_index=True
                        )


                # ==================================
                # 최종 분석
                # ==================================

                st.markdown("---")

                st.subheader(
                    "📌 최종 분석"
                )

                best = comparison.loc[
                    comparison[
                        "다양성 점수"
                    ].idxmax()
                ]

                worst = comparison.loc[
                    comparison[
                        "다양성 점수"
                    ].idxmin()
                ]

                st.success(
                    f"🌱 급식 다양성이 가장 높은 학교는 "
                    f"**{best['학교']}**이며 "
                    f"다양성 점수는 "
                    f"**{best['다양성 점수']}점**입니다."
                )

                st.warning(
                    f"🔁 다양성 점수가 가장 낮은 학교는 "
                    f"**{worst['학교']}**이며 "
                    f"**{worst['다양성 점수']}점**입니다."
                )

else:

    st.info(
        "👈 왼쪽에서 학교 3곳을 입력하고 "
        "'3개 학교 검색'을 눌러주세요."
    )
