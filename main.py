from datetime import datetime
import pandas as pd
import plotly.express as px
import requests
import streamlit as st
import pytz

# 1. 페이지 기본 설정 (타이틀, 레이아웃)
st.set_page_config(page_title="일별 박스오피스", page_icon="🎬", layout="wide")


# 2. 데이터 불러오기 함수 (1시간 동안 캐시 유지)
@st.cache_data(ttl=3600)
def fetch_boxoffice_data(target_date, api_key):
    """KOBIS API를 호출하여 해당 날짜의 박스오피스 데이터를 가져옵니다."""
    url = "https://www.kobis.or.kr/kobisopenapi/webservice/rest/boxoffice/searchDailyBoxOfficeList.json"
    params = {"key": api_key, "targetDt": target_date}

    try:
        response = requests.get(url, timeout=10)
        # HTTP 요청 자체가 실패한 경우 (예: 404, 500 에러)
        if response.status_code != 200:
            return (
                None,
                f"서버 응답 오류가 발생했습니다. (상태 코드: {response.status_code})",
            )

        data = response.json()

        # 인증키 오류 등으로 faultInfo가 반환된 경우
        if "faultInfo" in data:
            error_msg = data["faultInfo"].get("message", "알 수 없는 오류")
            return (
                None,
                f"API 오류 발생: {error_msg}\n'KOBIS_KEY' 비밀 금고(Secrets) 설정을 확인해 주세요.",
            )

        # 박스오피스 결과 확인
        box_office_result = data.get("boxOfficeResult", {})
        movie_list = box_office_result.get("dailyBoxOfficeList", [])

        # 영화 목록이 비어 있는 경우
        if not movie_list:
            return None, "그날은 아직 집계 전입니다."

        return movie_list, None

    except requests.exceptions.RequestException as e:
        return (
            None,
            f"네트워크 요청 중 오류가 발생했습니다: {e}\n인터넷 연결을 확인해 주세요.",
        )


# 3. 순위 증감 텍스트 반환 함수 (상승/하강/변화없음)
def format_rank_inten(val):
    """rankInten 값에 따라 상승(🔺), 하강(🔹), 변화없음(--) 기호를 반환합니다."""
    try:
        inten = int(val)
        if inten > 0:
            return f"🔺 +{inten}"
        elif inten < 0:
            return f"🔹 -{abs(inten)}"
        else:
            return "--"
    except (ValueError, TypeError):
        return "--"


# 4. 누적 관객수에 따른 이모지 부착 함수
def get_movie_name_with_emoji(name, audi_acc):
    """누적 관객수에 따라 영화명에 이모지를 붙여줍니다."""
    if audi_acc >= 10000000:
        return f"🎉🎉🎉 {name}"
    elif audi_acc >= 5000000:
        return f"🏆🏆 {name}"
    elif audi_acc >= 1000000:
        return f"🏆 {name}"
    return name


# 5. 메인 화면 구성
def main():
    st.title("🎬 일별 박스오피스")

    # [보안] Secrets에서 API 키 불러오기
    if "KOBIS_KEY" not in st.secrets:
        st.error(
            "🔑 API 키가 설정되지 않았습니다.\n\n"
            "Streamlit Cloud의 **Secrets** 항목에 `KOBIS_KEY = '발급받은_키'` 형태로 등록해 주세요."
        )
        return

    api_key = st.secrets["KOBIS_KEY"]

    # [시간 처리] 한국 시간(Asia/Seoul) 기준 계산
    korea_tz = pytz.timezone("Asia/Seoul")
    now_korea = datetime.now(korea_tz).date()
    yesterday = now_korea - pd.Timedelta(days=1)

    # [날짜 선택기] 달력에서 선택 가능 (최대 선택 가능 날짜: 어제)
    selected_date = st.date_input(
        "조회할 날짜를 선택하세요 (오늘 이후는 선택할 수 없습니다):",
        value=yesterday,
        max_value=yesterday,
    )

    target_dt_str = selected_date.strftime("%Y%m%d")  # API 호출용 (YYYYMMDD)
    display_date_str = selected_date.strftime("%Y년 %m월 %d일")  # 화면 표시용

    st.caption(f"📅 조회 기준일: {display_date_str}")

    # API 데이터 호출
    movie_list, error_message = fetch_boxoffice_data(target_dt_str, api_key)

    # 에러 또는 빈 데이터 발생 시 안내 메시지 출력
    if error_message:
        st.info(f"💡 {error_message}")
        return

    # 데이터프레임 변환
    df = pd.DataFrame(movie_list)

    # 숫자 타입 캐스팅 (문자열 -> 숫자)
    numeric_columns = ["rank", "rankInten", "audiCnt", "audiAcc", "scrnCnt"]
    for col in numeric_columns:
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

    # 순위 기준으로 정렬
    df = df.sort_values("rank").reset_index(drop=True)

    # 누적 관객수에 따른 이모지 추가 영화명 생성
    df["display_movieNm"] = df.apply(
        lambda row: get_movie_name_with_emoji(row["movieNm"], row["audiAcc"]),
        axis=1,
    )

    # 순위 변동 기호 가공
    df["rank_change"] = df["rankInten"].apply(format_rank_inten)

    # ----------------------------------------------------
    # [시각화 1] 1위 영화 지표 카드 (Metrics)
    # ----------------------------------------------------
    top_1 = df.iloc[0]
    st.markdown(f"### 🏆 1위: {top_1['display_movieNm']}")

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric(label="일일 관객수", value=f"{top_1['audiCnt']:,} 명")
    with col2:
        st.metric(label="누적 관객수", value=f"{top_1['audiAcc']:,} 명")
    with col3:
        st.metric(label="스크린수", value=f"{top_1['scrnCnt']:,} 개")

    st.divider()

    # ----------------------------------------------------
    # [시각화 2] 관객수 상위 5편 막대그래프 (Plotly)
    # ----------------------------------------------------
    st.subheader("📊 관객수 TOP 5")
    top_5_df = df.head(5)

    fig = px.bar(
        top_5_df,
        x="display_movieNm",
        y="audiCnt",
        text_auto=",.0f",  # 천 단위 콤마
        labels={"display_movieNm": "영화명", "audiCnt": "관객수 (명)"},
        color="audiCnt",
        color_continuous_scale="Reds",
    )
    fig.update_layout(
        xaxis_title="", yaxis_title="관객수", showlegend=False, height=400
    )
    st.plotly_chart(fig, use_container_width=True)

    st.divider()

    # ----------------------------------------------------
    # [시각화 3] 박스오피스 전체 순위 표 (Table)
    # ----------------------------------------------------
    st.subheader("📋 전체 박스오피스 순위")

    # 화면에 표시할 컬럼 정리
    table_df = df[
        [
            "rank",
            "rank_change",
            "display_movieNm",
            "openDt",
            "audiCnt",
            "audiAcc",
            "scrnCnt",
        ]
    ].copy()

    table_df.columns = [
        "순위",
        "순위변동",
        "영화명",
        "개봉일",
        "관객수",
        "누적관객",
        "스크린수",
    ]

    # 데이터 프레임 출력
    st.dataframe(
        table_df,
        use_container_width=True,
        hide_index=True,
        column_config={
            "순위": st.column_config.NumberColumn(format="%d위"),
            "순위변동": st.column_config.TextColumn(
                "순위변동",
                help="전일 대비 순위 변동 (🔺: 상승, 🔹: 하락, --: 동일)",
            ),
            "관객수": st.column_config.NumberColumn(format="%d명"),
            "누적관객": st.column_config.NumberColumn(format="%d명"),
            "스크린수": st.column_config.NumberColumn(format="%d개"),
        },
    )


if __name__ == "__main__":
    main()
