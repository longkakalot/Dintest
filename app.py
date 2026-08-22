import streamlit as st
from core import init_session_state
from pages import (
    page_1_intro,
    page_2_environment,
    page_3_headphone_confirm,
    page_4_volume_setup,
    page_5_choose_voice,
    page_6_instruction,
    page_7_main_test,
    page_8_result,
)

st.set_page_config(
    page_title="DIN Screening",
    page_icon="🎧",
    layout="wide"
)

init_session_state(st)

st.markdown(
    """
    <style>
    .block-container{
        max-width: 820px;
        padding-top: 0.8rem;
        padding-bottom: 1rem;
    }

    div[data-testid="column"]{
        padding-left: 0.03rem !important;
        padding-right: 0.03rem !important;
    }

    .stButton > button{
        border-radius: 8px !important;
        min-height: 30px !important;
        height: 30px !important;
        padding-top: 0rem !important;
        padding-bottom: 0rem !important;
        padding-left: 0.35rem !important;
        padding-right: 0.35rem !important;
        font-size: 15px !important;
        font-weight: 600 !important;
        margin-top: 0px !important;
        margin-bottom: 0px !important;
    }

    div[data-testid="stCheckbox"]{
        display:flex;
        justify-content:center;
        font-size:20px;
    }

    div[data-testid="stRadio"]{
        font-size:20px;
    }

    audio{
        width:100%;
    }
    </style>
    """,
    unsafe_allow_html=True
)

page = st.session_state.page

if page == 1:
    page_1_intro()
elif page == 2:
    page_2_environment()
elif page == 3:
    page_3_headphone_confirm()
elif page == 4:
    page_4_volume_setup()
elif page == 5:
    page_5_choose_voice()
elif page == 6:
    page_6_instruction()
elif page == 7:
    page_7_main_test()
elif page == 8:
    page_8_result()