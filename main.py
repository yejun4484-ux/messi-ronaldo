from datetime import datetime
import pandas as pd
import plotly.express as px
import requests
import streamlit as st
import pytz

# 1. 페이지 기본 설정 (타이틀, 레이아웃)
st.set_page_config(page_title="어제 박스오피스", page_icon="🎬", layout="wide")


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
            return (
                None,
                "조회된 영화 데이터가 없습니다. 집계 중이거나 해당 날짜의 데이터가 없을 수 있습니다.",
            )

        return movie_list, None

    except requests.exceptions.RequestException as e:
        return (
            None,
            f"네트워크 요청 중 오류가 발생했습니다: {e}\n인터넷 연결을 확인해 주세요.",
        )


# 3. 메인 화면 구성
def main():
    st.title("🎬 어제 일별 박스오피스")

    # [보안] Secrets에서 API 키 불러오기
    if "KOBIS_KEY" not in st.secrets:
        st.error(
            "🔑 API 키가 설정되지 않았습니다.\n\n"
            "Streamlit Cloud의 **Secrets** 항목에 `KOBIS_KEY = '발급받은_키'` 형태로 등록해 주세요."
        )
        return

    api_key = st.secrets["KOBIS_KEY"]

    # [시간 처리] 배포 서버 시계 기준이 아닌 한국 시간(Asia/Seoul) 기준 '어제' 날짜 계산
    korea_tz = pytz.timezone("Asia/Seoul")
    now_korea = datetime.now(korea_tz)
    # 어제 날짜 구하기 (timedelta 사용)
    yesterday = now_korea - pd.Timedelta(days=1)
    target_dt_str = yesterday.strftime("%Y%m%d")  # API용 (YYYYMMDD)
    display_date_str = yesterday.strftime(
        "%Y년 %m월 %d일"
    )  # 화면 표시용 (YYYY년 MM월 DD일)

    st.caption(f"📅 기준 일자: {display_date_str}")

    # API 데이터 호출
    movie_list, error_message = fetch_boxoffice_data(target_dt_str, api_key)

    # 에러 발생 시 안내 메시지 출력 후 중단
    if error_message:
        st.error(f"❌ 데이터를 가져오지 못했습니다.\n\n{error_message}")
        return

    # 데이터프레임 변환 및 타입 캐스팅 (문자열 -> 숫자)
    df = pd.DataFrame(movie_list)

    numeric_columns = ["rank", "audiCnt", "audiAcc", "scrnCnt"]
    for col in numeric_columns:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    # 순위 기준으로 정렬
    df = df.sort_values("rank").reset_index(drop=True)

    # ----------------------------------------------------
    # [시각화 1] 1위 영화 지표 카드 (Metrics)
    # ----------------------------------------------------
    top_1 = df.iloc[0]
    st.markdown(f"### 🏆 1위: {top_1['movieNm']}")

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
        x="movieNm",
        y="audiCnt",
        text_auto=",.0f",  # 막대 위에 관객수 천 단위 콤마 자동 표시
        labels={"movieNm": "영화명", "audiCnt": "관객수 (명)"},
        color="audiCnt",
        color_continuous_scale="Reds",
    )
    # 그래프 레이아웃 정돈
    fig.update_layout(
        xaxis_title="", yaxis_title="관객수", showlegend=False, height=400
    )
    st.plotly_chart(fig, use_container_width=True)

    st.divider()

    # ----------------------------------------------------
    # [시각화 3] 박스오피스 전체 순위 표 (Table)
    # ----------------------------------------------------
    st.subheader("📋 전체 박스오피스 순위")

    # 화면에 표시할 컬럼 정리 및 이름 변경
    table_df = df[
        ["rank", "movieNm", "openDt", "audiCnt", "audiAcc", "scrnCnt"]
    ].copy()
    table_df.columns = [
        "순위",
        "영화명",
        "개봉일",
        "관객수",
        "누적관객",
        "스크린수",
    ]

    # 숫자 포맷팅을 적용하여 테이블 출력
    st.dataframe(
        table_df,
        use_container_width=True,
        hide_index=True,
        column_config={
            "순위": st.column_config.NumberColumn(format="%d위"),
            "관객수": st.column_config.NumberColumn(format="%d명"),
            "누적관객": st.column_config.NumberColumn(format="%d명"),
            "스크린수": st.column_config.NumberColumn(format="%d개"),
        },
    )


if __name__ == "__main__":
    main()
