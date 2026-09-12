import streamlit as st
import requests
import pandas as pd
import re
from collections import Counter

# -----------------------------------------
# 기본 설정
# -----------------------------------------
st.set_page_config(
    page_title="우리 학교 급식 분석",
    page_icon="🍚",
    layout="wide"
)

st.title("🍚 우리 학교 급식 메뉴 분석")
st.write("나이스 급식 데이터를 이용해 메뉴 반복과 다양성을 분석합니다.")

BASE_URL = "https://open.neis.go.kr/hub"


# -----------------------------------------
# 학교 검색
# -----------------------------------------
def search_school(school_name):
    url = f"{BASE_URL}/schoolInfo"

    params = {
        "Type": "json",
        "SCHUL_NM": school_name
    }

    response = requests.get(url, params=params, timeout=10)
    data = response.json()

    try:
        rows = data["schoolInfo"][1]["row"]
        return rows

    except (KeyError, IndexError):
        return []


# -----------------------------------------
# 급식 데이터 가져오기
# -----------------------------------------
def get_meal_data(atpt_code, school_code, start_date, end_date):

    url = f"{BASE_URL}/mealServiceDietInfo"

    params = {
        "Type": "json",
        "ATPT_OFCDC_SC_CODE": atpt_code,
        "SD_SCHUL_CODE": school_code,
        "MMEAL_SC_CODE": "2",
        "MLSV_FROM_YMD": start_date,
        "MLSV_TO_YMD": end_date
    }

    response = requests.get(url, params=params, timeout=10)
    data = response.json()

    try:
        rows = data["mealServiceDietInfo"][1]["row"]
        return rows

    except (KeyError, IndexError):
        return []


# -----------------------------------------
# 메뉴 전처리
# -----------------------------------------
def clean_menu(menu):

    # 알레르기 번호 제거
    menu = re.sub(r"\([^)]*\)", "", menu)

    # 숫자 제거
    menu = re.sub(r"\d+", "", menu)

    # 특수문자 제거
    menu = re.sub(r"[*]", "", menu)

    # 공백 정리
    menu = menu.strip()

    return menu


# -----------------------------------------
# 사이드바
# -----------------------------------------
st.sidebar.header("⚙️ 검색 설정")

school_name = st.sidebar.text_input(
    "학교 이름",
    placeholder="예: 인천고등학교"
)

start_date = st.sidebar.date_input(
    "시작 날짜",
    pd.Timestamp("2026-03-01")
)

end_date = st.sidebar.date_input(
    "끝 날짜",
    pd.Timestamp("2026-07-31")
)


# -----------------------------------------
# 학교 검색
# -----------------------------------------
if school_name:

    if st.sidebar.button("학교 검색"):

        with st.spinner("학교를 검색하는 중..."):

            schools = search_school(school_name)

        if schools:

            st.session_state["schools"] = schools

        else:

            st.error("학교 정보를 찾을 수 없습니다.")


# -----------------------------------------
# 학교 선택
# -----------------------------------------
if "schools" in st.session_state:

    schools = st.session_state["schools"]

    school_options = [
        f"{s['SCHUL_NM']} ({s['LCTN_SC_NM']})"
        for s in schools
    ]

    selected = st.selectbox(
        "학교를 선택하세요",
        school_options
    )

    index = school_options.index(selected)

    school = schools[index]

    st.success(
        f"선택된 학교: {school['SCHUL_NM']} "
        f"({school['LCTN_SC_NM']})"
    )


    # -----------------------------------------
    # 급식 분석 시작
    # -----------------------------------------
    if st.button("🍚 급식 데이터 분석하기"):

        if start_date > end_date:

            st.error("시작 날짜가 끝 날짜보다 늦습니다.")

        else:

            with st.spinner("급식 데이터를 가져오는 중..."):

                meals = get_meal_data(
                    school["ATPT_OFCDC_SC_CODE"],
                    school["SD_SCHUL_CODE"],
                    start_date.strftime("%Y%m%d"),
                    end_date.strftime("%Y%m%d")
                )

            if not meals:

                st.warning(
                    "해당 기간에 급식 데이터가 없습니다."
                )

            else:

                # -----------------------------------------
                # 데이터프레임 생성
                # -----------------------------------------
                df = pd.DataFrame(meals)

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

                # -----------------------------------------
                # 메뉴 분리
                # -----------------------------------------
                all_menus = []

                for menu_text in df["메뉴"]:

                    # <br/> 기준으로 메뉴 분리
                    menus = re.split(
                        r"<br\s*/?>",
                        menu_text
                    )

                    for menu in menus:

                        menu = clean_menu(menu)

                        if menu:
                            all_menus.append(menu)

                # 메뉴 등장 횟수
                menu_count = Counter(all_menus)

                menu_df = pd.DataFrame(
                    menu_count.items(),
                    columns=["메뉴", "등장횟수"]
                )

                menu_df = menu_df.sort_values(
                    "등장횟수",
                    ascending=False
                )

                # -----------------------------------------
                # 핵심 지표
                # -----------------------------------------
                total_meal_days = len(df)

                unique_menu_count = len(
                    set(all_menus)
                )

                total_menu_count = len(all_menus)

                # 다양성 점수
                diversity_score = (
                    unique_menu_count /
                    total_menu_count * 100
                )

                # -----------------------------------------
                # 상단 지표
                # -----------------------------------------
                st.subheader("📊 급식 분석 결과")

                col1, col2, col3, col4 = st.columns(4)

                col1.metric(
                    "급식 제공일",
                    f"{total_meal_days}일"
                )

                col2.metric(
                    "전체 메뉴 수",
                    f"{total_menu_count}개"
                )

                col3.metric(
                    "서로 다른 메뉴",
                    f"{unique_menu_count}개"
                )

                col4.metric(
                    "🌱 다양성 점수",
                    f"{diversity_score:.1f}점"
                )


                # -----------------------------------------
                # 메뉴 반복 TOP 10
                # -----------------------------------------
                st.subheader(
                    "🔥 가장 많이 반복된 메뉴 TOP 10"
                )

                top10 = menu_df.head(10)

                st.bar_chart(
                    top10.set_index("메뉴")["등장횟수"]
                )


                # -----------------------------------------
                # 표
                # -----------------------------------------
                st.dataframe(
                    top10,
                    use_container_width=True,
                    hide_index=True
                )


                # -----------------------------------------
                # 반복 메뉴 분석
                # -----------------------------------------
                st.subheader(
                    "🔁 반복 메뉴 분석"
                )

                repeated = menu_df[
                    menu_df["등장횟수"] >= 3
                ]

                if len(repeated) > 0:

                    st.write(
                        f"3회 이상 등장한 메뉴는 "
                        f"**{len(repeated)}개**입니다."
                    )

                    st.dataframe(
                        repeated,
                        use_container_width=True,
                        hide_index=True
                    )

                else:

                    st.info(
                        "3회 이상 반복된 메뉴가 없습니다."
                    )


                # -----------------------------------------
                # 월별 다양성
                # -----------------------------------------
                st.subheader(
                    "📅 월별 급식 다양성"
                )

                df["월"] = df["날짜"].dt.to_period("M")

                monthly_data = []

                for month, group in df.groupby("월"):

                    menus = []

                    for menu_text in group["메뉴"]:

                        split_menus = re.split(
                            r"<br\s*/?>",
                            menu_text
                        )

                        for menu in split_menus:

                            menu = clean_menu(menu)

                            if menu:
                                menus.append(menu)

                    if menus:

                        unique = len(set(menus))
                        total = len(menus)

                        score = unique / total * 100

                        monthly_data.append({
                            "월": str(month),
                            "메뉴 수": total,
                            "중복 제거 메뉴 수": unique,
                            "다양성 점수": round(score, 1)
                        })

                monthly_df = pd.DataFrame(
                    monthly_data
                )

                if not monthly_df.empty:

                    st.line_chart(
                        monthly_df.set_index("월")[
                            "다양성 점수"
                        ]
                    )

                    st.dataframe(
                        monthly_df,
                        use_container_width=True,
                        hide_index=True
                    )


                # -----------------------------------------
                # 결론
                # -----------------------------------------
                st.subheader("💡 분석 결과")

                most_repeated = menu_df.iloc[0]

                st.write(
                    f"가장 많이 등장한 메뉴는 "
                    f"**{most_repeated['메뉴']}**이며, "
                    f"총 **{most_repeated['등장횟수']}회** "
                    f"등장했습니다."
                )

                if diversity_score >= 70:

                    st.success(
                        "🌱 메뉴 다양성이 높은 편입니다."
                    )

                elif diversity_score >= 40:

                    st.warning(
                        "⚠️ 메뉴가 어느 정도 반복되고 있습니다."
                    )

                else:

                    st.error(
                        "🚨 메뉴 반복 비율이 높은 편입니다."
                    )


                # -----------------------------------------
                # 원본 데이터
                # -----------------------------------------
                with st.expander("📋 원본 급식 데이터 보기"):

                    st.dataframe(
                        df,
                        use_container_width=True,
                        hide_index=True
                    )

else:

    st.info(
        "👈 왼쪽에서 학교 이름을 입력하고 "
        "'학교 검색'을 눌러주세요."
    )
