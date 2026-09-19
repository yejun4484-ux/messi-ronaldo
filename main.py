# main.py — 여러 변수로 총 관객을 예측한다
import streamlit as st
import pandas as pd
from sklearn.linear_model import LinearRegression
from sklearn.metrics import r2_score, mean_absolute_error

DAILY = "https://raw.githubusercontent.com/greatsong/modudata/main/data/kobis_daily.csv"
MOVIES = "https://raw.githubusercontent.com/greatsong/modudata/main/data/kobis_movies.csv"

st.header("영화 흥행 예측")
st.caption("사후 집계 데이터를 사용한 교육용 비교입니다. 실제 개봉 전 예측 성능을 뜻하지 않습니다.")

@st.cache_data
def load_data():
    daily = pd.read_csv(DAILY, dtype={"영화코드": str})
    movies = pd.read_csv(MOVIES, dtype={"movieCd": str})
    # 영화별 표는 일별 표에서 만들어진다. 두 표를 잇는 열은 영화코드다.
    return daily, movies

daily, movies = load_data()
df = movies.sort_values("movieCd").reset_index(drop=True)
# 열 편 중 앞 세 편을 테스트용으로 떼어 둔다 (누가 해도 같은 결과가 나오도록)
is_test = df.index % 10 < 3
train, test = df[~is_test], df[is_test]
st.caption(f"훈련용 {len(train)}편 · 테스트용 {len(test)}편 · 전체 {len(df)}편")
st.caption(f"기준 기간 {daily['날짜'].min()} ~ {daily['날짜'].max()} · 박스오피스 상위 10위 기록")
st.dataframe(df.head(10))   # 표의 맨 위 열 줄

기본 = {"첫 관측일 스크린수": "first_scrn", "첫 관측일 상영횟수": "first_show", "성수기 개봉": "peak"}
추가 = {"첫 주 관객": "first_week_audi"}

st.subheader("변수 고르기")
picked = [col for name, col in {**기본, **추가}.items() if st.checkbox(name, value=col in 기본.values())]
if not picked:
    st.warning("변수를 하나 이상 골라 주세요.")
    st.stop()

model = LinearRegression().fit(train[picked], train["total_audi"])
pred = model.predict(test[picked])
c1, c2 = st.columns(2)
c1.metric("테스트용 데이터로 평가한 점수 (R²)", f"{r2_score(test['total_audi'], pred):.3f}")
c2.metric("평균 오차", f"{mean_absolute_error(test['total_audi'], pred):,.0f}명")

import plotly.express as px

바닥 = 1000
표시 = pd.DataFrame({"실제": test["total_audi"].values, "예측": pred})
표시["예측(표시용)"] = 표시["예측"].clip(lower=바닥)   # 음수 예측도 그래프 바닥에 남긴다
fig = px.scatter(표시, x="실제", y="예측(표시용)", log_x=True, log_y=True,
                 labels={"실제": "실제 총 관객 수", "예측(표시용)": "예측 총 관객 수"})
끝 = [표시["실제"].min(), 표시["실제"].max()]
fig.add_shape(type="line", x0=끝[0], y0=끝[0], x1=끝[1], y1=끝[1], line=dict(dash="dash"))
st.plotly_chart(fig, use_container_width=True)

낮음 = int((표시["예측"] < 바닥).sum())
if 낮음:
    st.caption(f"예측이 1,000명보다 작게 나온 영화 {낮음}편은 그래프 바닥에 표시했습니다. 회귀는 음수도 예측합니다.")
