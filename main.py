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
st.write("나이스 교육정보 개방 포털의 급식 데이터를 이용하여 3개 학교를 비교합니다.")

BASE_URL = "https://open.neis.go.kr/hub"


# ==========================================
# 학교 검색
# ==========================================

def search_school(school_name):

    url = f"{BASE_URL}/schoolInfo"

    params = {
        "Type": "json",
        "SCHUL_NM": school_name
    }

    try:
        response = requests.get(
            url,
            params=params,
            timeout=10
        )

        data = response.json()

        if "schoolInfo" in data:
            return data["schoolInfo"][1]["row"]

    except Exception:
        pass

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
        "Type": "json",
        "ATPT_OFCDC_SC_CODE": atpt_code,
        "SD_SCHUL_CODE": school_code,
        "MMEAL_SC_CODE": "2",
        "MLSV_FROM_YMD": start_date,
        "MLSV_TO_YMD": end_date
    }

    try:

        response = requests.get(
            url,
            params=params,
            timeout=10
        )

        data = response.json()

        if "mealServiceDietInfo" in data:
            return data["mealServiceDietInfo"][1]["row"]

    except Exception:
        pass

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

    # 특수문자 제거
    menu = re.sub(
        r"[*]",
        "",
        menu
    )

    # 앞뒤 공백 제거
    menu = menu.strip()

    return menu


# ==========================================
# 학교 데이터 분석
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

    # 필요한 열만 사용
    df = df[
        [
            "MLSV_YMD",
            "DDISH_NM",
            "CAL_INFO"
        ]
    ]

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

    # ======================================
    # 메뉴 분리
    # ======================================

    all_menus = []

    for menu_text in df["메뉴"]:

        menus = re.split(
            r"<br\s*/?>",
            menu_text
        )

        for menu in menus:

            menu = clean_menu(menu)

            if menu:
                all_menus.append(menu)

    # ======================================
    # 메뉴 등장 횟수
    # ======================================

    menu_count = Counter(all_menus)

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

    # ======================================
    # 칼로리 숫자로 변환
    # ======================================

    calories = []

    for value in df["칼로리"]:

        try:

            # 예: "850.2 Kcal"
            number = re.search(
                r"\d+(\.\d+)?",
                str(value)
            )

            if number:
                calories.append(
                    float(number.group())
                )

        except Exception:
            pass

    # ======================================
    # 다양성 점수
    # ======================================

    total_menu_count = len(all_menus)

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

    # ======================================
    # 평균 칼로리
    # ======================================

    if calories:

        average_calorie = sum(calories) / len(calories)

    else:

        average_calorie = 0

    # ======================================
    # 결과
    # ======================================

    return {

        "학교명": school["SCHUL_NM"],

        "급식일수": len(df),

        "전체메뉴수": total_menu_count,

        "서로다른메뉴": unique_menu_count,

        "다양성점수": round(
            diversity_score,
            1
        ),

        "평균칼로리": round(
            average_calorie,
            1
        ),

        "메뉴분석": menu_df,

        "원본데이터": df
    }


# ==========================================
# 사이드바
# ==========================================

st.sidebar.header("⚙️ 비교 설정")

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

    school_names.append(name)


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
# 학교 검색 버튼
# ==========================================

if st.sidebar.button(
    "🔎 3개 학교 검색"
):

    st.session_state["school_results"] = {}

    for i, name in enumerate(school_names):

        if not name:
            continue

        with st.spinner(
            f"{name} 검색 중..."
        ):

            results = search_school(name)

        st.session_state[
            "school_results"
        ][i] = results


# ==========================================
# 학교 선택
# ==========================================

selected_schools = []

if "school_results" in st.session_state:

    st.subheader("🏫 학교 선택")

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

        index = options.index(selected)

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

            progress = st.progress(0)

            for i, school in enumerate(
                selected_schools
            ):

                with st.spinner(
                    f"{school['SCHUL_NM']} 급식 분석 중..."
                ):

                    result = analyze_school(
                        school,
                        start_date,
                        end_date
                    )

                if result:

                    results.append(result)

                progress.progress(
                    (i + 1) / 3
                )

            # ==================================
            # 데이터가 없는 경우
            # ==================================

            if len(results) == 0:

                st.error(
                    "급식 데이터를 찾을 수 없습니다."
                )

            else:

                # ==================================
                # 비교 데이터프레임
                # ==================================

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


                # ==================================
                # 결과 요약
                # ==================================

                st.subheader(
                    "📊 학교별 비교 결과"
                )

                st.dataframe(
                    comparison,
                    use_container_width=True,
                    hide_index=True
                )


                # ==================================
                # 다양성 점수
                # ==================================

                st.subheader(
                    "🌱 급식 다양성 비교"
                )

                diversity_chart = comparison[
                    [
                        "학교",
                        "다양성 점수"
                    ]
                ].set_index("학교")

                st.bar_chart(
                    diversity_chart
                )


                # ==================================
                # 평균 칼로리
                # ==================================

                st.subheader(
                    "🔥 평균 칼로리 비교"
                )

                calorie_chart = comparison[
                    [
                        "학교",
                        "평균 칼로리"
                    ]
                ].set_index("학교")

                st.bar_chart(
                    calorie_chart
                )


                # ==================================
                # 순위
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

                ranking.index += 1

                ranking.insert(
                    0,
                    "순위",
                    ranking.index
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
                # 학교별 반복 메뉴
                # ==================================

                st.subheader(
                    "🔁 학교별 가장 많이 반복된 메뉴"
                )

                cols = st.columns(3)

                for i, result in enumerate(
                    results
                ):

                    with cols[i]:

                        st.write(
                            f"### {result['학교명']}"
                        )

                        top10 = (
                            result["메뉴분석"]
                            .head(10)
                        )

                        st.dataframe(
                            top10,
                            use_container_width=True,
                            hide_index=True
                        )


                # ==================================
                # 최종 분석
                # ==================================

                st.subheader(
                    "💡 최종 분석"
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

                calorie_high = comparison.loc[
                    comparison[
                        "평균 칼로리"
                    ].idxmax()
                ]

                calorie_low = comparison.loc[
                    comparison[
                        "평균 칼로리"
                    ].idxmin()
                ]

                st.success(
                    f"🌱 급식 다양성이 가장 높은 학교는 "
                    f"**{best['학교']}**이며 "
                    f"다양성 점수는 "
                    f"**{best['다양성 점수']}점**입니다."
                )

                st.warning(
                    f"🔁 비교한 학교 중 다양성 점수가 "
                    f"가장 낮은 학교는 "
                    f"**{worst['학교']}**이며 "
                    f"**{worst['다양성 점수']}점**입니다."
                )

                st.info(
                    f"🔥 평균 칼로리가 가장 높은 학교는 "
                    f"**{calorie_high['학교']}** "
                    f"({calorie_high['평균 칼로리']} kcal)이고, "
                    f"가장 낮은 학교는 "
                    f"**{calorie_low['학교']}** "
                    f"({calorie_low['평균 칼로리']} kcal)입니다."
                )


# ==========================================
# 처음 화면
# ==========================================

else:

    st.info(
        "👈 왼쪽에서 3개 학교의 이름을 입력한 뒤 "
        "'3개 학교 검색'을 눌러주세요."
    )
