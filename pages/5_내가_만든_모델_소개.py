
import streamlit as st
import pandas as pd

# ==========================================
# 페이지 설정
# ==========================================
st.set_page_config(
    page_title="내가 만든 모델 소개",
    page_icon="📝",
    layout="wide",
)

st.title("📝 내가 만든 모델 소개")
st.write(
    "내가 만든 뇌졸중 예측 모델을 설명하고, "
    "고치기 전과 고친 뒤의 성능을 비교해 봅시다."
)
st.info(
    "이 페이지는 직접 작성하는 공간입니다. "
    "다른 페이지의 값을 자동으로 가져오지 않으며, "
    "작성한 내용은 현재 화면의 세션에만 유지됩니다."
)

# ==========================================
# 입력 항목
# ==========================================
설명_항목 = [
    "무슨 데이터입니까",
    "무엇을 보고 맞힙니까",
    "무엇을 고쳤습니까",
    "이 모델을 검진센터가 사용해도 됩니까",
    "이 모델이 못 하는 것 한 가지",
]

# ==========================================
# 성능 비교표
# ==========================================
성능_항목 = [
    "정확도",
    "재현율",
    "F1",
    "찾아낸 환자",
    "헛짚은 사람",
]

표_초기값 = pd.DataFrame(
    {
        "평가 항목": 성능_항목,
        "고치기 전": [""] * len(성능_항목),
        "고친 뒤": [""] * len(성능_항목),
    }
)

if "모델소개_성능표" not in st.session_state:
    st.session_state["모델소개_성능표"] = 표_초기값.copy()

# ==========================================
# 탭
# ==========================================
작성탭, 모아보기탭 = st.tabs(
    ["✏️ 작성하기", "📄 한 장으로 보기"]
)

# ==========================================
# 탭 1: 작성하기
# ==========================================
with 작성탭:
    st.subheader("1. 내가 만든 모델 설명하기")
    st.caption("각 항목에 자신의 생각을 여러 줄로 적어 보세요.")

    for i, 항목 in enumerate(설명_항목, start=1):
        st.markdown(f"**{i}. {항목}**")

        st.text_area(
            label=항목,
            placeholder=f"여기에 '{항목}'에 대한 내용을 적으세요.",
            height=120,
            key=f"모델소개_설명_{i}",
            label_visibility="collapsed",
        )

    st.divider()

    st.subheader("2. 고치기 전과 고친 뒤의 성능 비교")
    st.write(
        "앞 페이지에서 확인한 값을 직접 옮겨 적으세요. "
        "비율은 정확도·재현율·F1에 맞는 형식으로, "
        "환자 수는 사람 수로 입력하면 됩니다."
    )

    편집된_표 = st.data_editor(
        st.session_state["모델소개_성능표"],
        hide_index=True,
        use_container_width=True,
        num_rows="fixed",
        disabled=["평가 항목"],
        column_config={
            "평가 항목": st.column_config.TextColumn(
                "평가 항목",
                width="medium",
            ),
            "고치기 전": st.column_config.TextColumn(
                "고치기 전",
                help="수정하기 전 모델의 값을 입력하세요.",
            ),
            "고친 뒤": st.column_config.TextColumn(
                "고친 뒤",
                help="수정한 뒤 모델의 값을 입력하세요.",
            ),
        },
        key="모델소개_성능표_편집기",
    )

    # 입력된 표를 현재 세션에만 반영한다.
    st.session_state["모델소개_성능표"] = 편집된_표.copy()

    st.caption(
        "예: 정확도 0.90 또는 90%, 찾아낸 환자 18명. "
        "앞 페이지의 평가 기준과 단위를 확인하세요."
    )

    st.divider()
    st.success(
        "작성한 내용은 아래 '한 장으로 보기' 탭에서 "
        "모아 확인할 수 있습니다."
    )

# ==========================================
# 탭 2: 한 장으로 보기
# ==========================================
with 모아보기탭:
    st.subheader("내가 만든 모델 소개서")
    st.caption("작성한 내용을 한곳에 모아 확인하는 화면입니다.")

    # 1. 설명 다섯 가지
    for i, 항목 in enumerate(설명_항목, start=1):
        st.markdown(f"### {i}. {항목}")

        내용 = st.session_state.get(
            f"모델소개_설명_{i}", ""
        ).strip()

        if 내용:
            st.markdown(내용)
        else:
            st.caption("아직 적지 않았습니다.")

    st.divider()

    # 2. 성능 비교표
    st.markdown("### 6. 고치기 전과 고친 뒤의 성능 비교")

    현재_표 = st.session_state["모델소개_성능표"].copy()

    # 입력하지 않은 칸은 비어 있음 대신 알아보기 쉬운 문구로 표시한다.
    for 열 in ["고치기 전", "고친 뒤"]:
        현재_표[열] = 현재_표[열].apply(
            lambda 값: (
                값.strip() if isinstance(값, str) and 값.strip()
                else "아직 적지 않았습니다"
            )
        )

    st.dataframe(
        현재_표,
        hide_index=True,
        use_container_width=True,
        column_config={
            "평가 항목": st.column_config.TextColumn(
                "평가 항목",
                width="medium",
            ),
            "고치기 전": st.column_config.TextColumn(
                "고치기 전",
                width="large",
            ),
            "고친 뒤": st.column_config.TextColumn(
                "고친 뒤",
                width="large",
            ),
        },
    )

    st.divider()
    st.caption(
        "이 소개서는 화면에서 확인하기 위한 것입니다. "
        "파일로 저장하거나 외부로 전송하지 않습니다. "
        "페이지를 새로 시작하거나 세션이 종료되면 "
        "작성 내용이 유지되지 않을 수 있습니다."
    )
