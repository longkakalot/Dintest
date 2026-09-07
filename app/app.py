import streamlit as st
from core import init_session_state
from pages import (
    page_1_intro,
    page_2_profile,
    page_3_health,
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
    layout="wide",
    initial_sidebar_state="collapsed",
)

init_session_state(st)

st.markdown(
    """
    <style>
    :root{
        --din-blue:#075fb8;
        --din-navy:#12304a;
        --din-bg:#f5f9fd;
        --din-border:#dbe7f2;
        --din-muted:#607386;
    }

    .stApp{
        background:
          radial-gradient(circle at 8% 5%,rgba(57,150,220,.13),transparent 30%),
          radial-gradient(circle at 92% 12%,rgba(15,100,180,.10),transparent 26%),
          linear-gradient(180deg,#f2f8fe 0,#f8fbfd 42%,#f6f8fb 100%);
    }

    header[data-testid="stHeader"]{background:transparent;}
    #MainMenu, footer, div[data-testid="stToolbar"]{visibility:hidden;}

    .block-container{
        width:min(100%, 900px);
        max-width:900px;
        padding:1.25rem 1.6rem 2.5rem;
        margin:0 auto;
    }

    .block-container > div[data-testid="stVerticalBlock"]{gap:.8rem;}
    label, p, button, input{line-height:1.45 !important;}

    .din-card{
        background:rgba(255,255,255,.96);
        border:1px solid var(--din-border);
        border-radius:22px;
        padding:22px 18px;
        box-shadow:0 14px 38px rgba(15,61,94,.10);
    }

    .din-stepbar{display:flex;align-items:center;justify-content:center;margin:2px auto 22px;max-width:690px;padding:12px 14px;background:rgba(255,255,255,.82);border:1px solid rgba(205,224,240,.9);border-radius:18px;box-shadow:0 8px 24px rgba(20,65,100,.07);}
    .din-step-node{--step-color:#2196d2;--step-light:#8fd9f5;width:32px;height:32px;flex:0 0 32px;border-radius:50%;display:grid;place-items:center;background:linear-gradient(145deg,#fff,#dfe9f0);border:2px solid #d2e0eb;color:#7990a3;font-size:12px;font-weight:900;box-shadow:inset 2px 2px 4px rgba(255,255,255,.95),inset -3px -3px 6px rgba(52,82,103,.12),0 4px 8px rgba(34,71,98,.12);transition:.2s ease;}
    .din-step-node.color-1{--step-color:#1d78d0;--step-light:#67c4ff;}
    .din-step-node.color-2{--step-color:#7357c9;--step-light:#b79cff;}
    .din-step-node.color-3{--step-color:#12a5a0;--step-light:#63ded5;}
    .din-step-node.color-4{--step-color:#28a868;--step-light:#7ee0a9;}
    .din-step-node.color-5{--step-color:#d49b19;--step-light:#ffda68;}
    .din-step-node.color-6{--step-color:#e17b2f;--step-light:#ffb773;}
    .din-step-node.color-7{--step-color:#dc536a;--step-light:#ff9aaa;}
    .din-step-node.color-8{--step-color:#b94ca0;--step-light:#ee91d8;}
    .din-step-node.color-9{--step-color:#3476aa;--step-light:#78b8e7;}
    .din-step-node.done{background:linear-gradient(145deg,var(--step-light),var(--step-color));border-color:rgba(255,255,255,.8);color:#fff;text-shadow:0 1px 2px rgba(0,0,0,.2);}
    .din-step-node.active{background:radial-gradient(circle at 32% 24%,#fff 0 5%,var(--step-light) 18%,var(--step-color) 68%);border-color:#fff;color:#fff;text-shadow:0 1px 2px rgba(0,0,0,.28);box-shadow:inset 3px 3px 5px rgba(255,255,255,.5),inset -4px -5px 7px rgba(0,35,80,.22),0 0 0 5px color-mix(in srgb,var(--step-color) 18%,transparent),0 7px 13px rgba(28,67,96,.25);transform:scale(1.14) translateY(-1px);}
    .din-step-line{height:6px;min-width:12px;flex:1;max-width:48px;background:linear-gradient(180deg,#edf3f7,#cddce7);border-radius:99px;box-shadow:inset 0 2px 3px rgba(49,79,101,.14),0 1px 0 #fff;}
    .din-step-line.done{background:linear-gradient(180deg,#75cdf0,#2189c8);box-shadow:inset 0 2px 2px rgba(255,255,255,.38),0 2px 4px rgba(30,111,161,.18);}
    .din-simple-title{text-align:center;color:var(--din-navy);font-size:26px;font-weight:850;line-height:1.25;margin:2px 0 22px;text-transform:uppercase;letter-spacing:.035em;}

    .din-kicker{font-size:12px;font-weight:800;letter-spacing:.12em;text-transform:uppercase;color:#5680a5;text-align:center;}
    .din-title{font-size:27px;line-height:1.2;font-weight:850;color:var(--din-navy);text-align:center;margin:7px 0 8px;text-transform:uppercase;letter-spacing:.025em;}
    .din-subtitle{font-size:15px;line-height:1.55;color:#607386;text-align:center;margin:0 0 16px;}

    div[data-testid="stColumn"],
    div[data-testid="column"]{
        padding-left: 0.03rem !important;
        padding-right: 0.03rem !important;
    }

    .st-key-keypad-wrap,
    .st-key-test-nav{max-width:440px;margin-left:auto;margin-right:auto;}
    .st-key-intro-action{max-width:420px;margin-left:auto;margin-right:auto;}
    .st-key-intro-logo{width:100%;max-width:420px;margin-left:auto;margin-right:auto;}
    .st-key-intro-logo div[data-testid="stImage"]{width:100%;display:flex;justify-content:center;}
    .st-key-intro-logo img{width:100% !important;max-width:420px !important;height:auto !important;object-fit:contain;}
    .st-key-result-action{max-width:320px;margin-left:auto;margin-right:auto;}

    .stButton > button{
        border-radius:12px !important;
        min-height:46px !important;
        height:auto !important;
        padding:.55rem .7rem !important;
        font-size:15px !important;
        font-weight:750 !important;
        border:1px solid #cbdceb !important;
        box-shadow:0 3px 10px rgba(20,65,100,.07) !important;
        margin-top: 0px !important;
        margin-bottom: 0px !important;
    }
    .stButton > button:hover{border-color:#408bc5 !important;color:#075fb8 !important;transform:translateY(-1px);}
    .stButton > button[kind="primary"]{background:linear-gradient(135deg,#075fb8,#0c82cf) !important;color:#fff !important;border:none !important;}

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

    div[data-baseweb="select"] > div{
        min-height:48px;
        border-radius:12px;
        border-color:#cbdceb;
        background:#fff;
    }

    div[data-testid="stMultiSelect"] span[data-baseweb="tag"]{background:#e2f1fc;color:#164c74;border-radius:8px;}
    div[data-testid="stTextInput"] input{min-height:48px;border-radius:12px;}
    div[data-testid="stAlert"]{border-radius:14px;margin:.15rem 0;}
    div[data-testid="stCaptionContainer"]{margin:.1rem 0 .2rem;}
    img{max-width:100%;height:auto;}
    div[data-testid="stImage"]{display:flex;justify-content:center;}

    div[data-testid="stProgress"]{margin-top:.2rem;}
    .din-volume-instruction{font-size:clamp(16px,2.1vw,20px);line-height:1.45;}
    .din-volume-note{font-size:13px;line-height:1.35;}
    .din-test-instruction{font-size:18px;line-height:1.4;}

    /* Toàn bộ st.columns trong ứng dụng là hàng điều hướng 2 nút.
       Khóa thành grid cân giữa để không lệch trên laptop/tablet. */
    div[data-testid="stHorizontalBlock"]{
        display:grid !important;
        grid-template-columns:repeat(2,minmax(0,1fr)) !important;
        gap:1rem !important;
        width:100% !important;
        max-width:540px;
        margin-left:auto !important;
        margin-right:auto !important;
        align-items:stretch !important;
    }
    div[data-testid="stHorizontalBlock"] > div[data-testid="stColumn"],
    div[data-testid="stHorizontalBlock"] > div[data-testid="column"]{
        width:100% !important;
        min-width:0 !important;
        flex:none !important;
    }
    .st-key-keypad-wrap div[data-testid="stHorizontalBlock"]{
        grid-template-columns:repeat(3,minmax(0,1fr)) !important;
        max-width:440px;
        gap:.5rem !important;
    }
    .st-key-keypad-wrap div[data-testid="stVerticalBlock"]{gap:.28rem !important;}
    .din-keypad-display{height:34px !important;margin-bottom:2px !important;}

    @media (max-width: 820px){
        .block-container{max-width:700px;padding:1rem 1.1rem 2rem;}
        .block-container > div[data-testid="stVerticalBlock"]{gap:.72rem;}
    }

    @media (max-width: 520px){
        .block-container{width:100% !important;max-width:100% !important;padding:.35rem .55rem .75rem !important;overflow-x:hidden;}
        .block-container > div[data-testid="stVerticalBlock"]{gap:.62rem;}
        .din-card{padding:19px 15px;border-radius:18px;}
        .din-title{font-size:24px;}
        .din-stepbar{padding:10px 8px;margin-bottom:16px;border-radius:15px;}
        .din-step-node{width:25px;height:25px;flex-basis:25px;font-size:10px;}
        .din-step-node.active{box-shadow:0 0 0 3px rgba(7,95,184,.12);}
        .din-step-line{min-width:4px;height:2px;}
        .din-simple-title{font-size:22px;margin-bottom:16px;}
        .din-volume-instruction{font-size:16px !important;line-height:1.35 !important;margin-bottom:4px !important;}
        .din-volume-note{font-size:11px !important;line-height:1.25 !important;padding:6px 8px !important;margin-top:-4px !important;}
        .din-test-instruction{font-size:16px !important;line-height:1.32 !important;}
        div[data-testid="stColumn"],div[data-testid="column"]{min-width:0 !important;}
        .st-key-keypad-wrap,.st-key-test-nav{width:100%;max-width:370px;}
        .block-container [style*="font-size:22px"]{font-size:16px !important;line-height:1.4 !important;}
        .stButton > button{min-height:42px !important;padding:.4rem .45rem !important;font-size:14px !important;}
        .st-key-keypad-wrap .stButton > button{min-height:34px !important;padding:.18rem .35rem !important;}
        .st-key-test-nav .stButton > button{min-height:38px !important;padding:.28rem .4rem !important;}
    }

    @media (min-width:521px) and (max-width:900px){
        .block-container{width:100% !important;max-width:760px !important;padding:.75rem 1rem 1.2rem !important;}
    }

    @media (max-width:520px){
        div[data-testid="stHorizontalBlock"]{gap:.55rem !important;max-width:100%;}
        .st-key-keypad-wrap div[data-testid="stHorizontalBlock"]{gap:.35rem !important;}
    }
    </style>
    """,
    unsafe_allow_html=True
)

page = st.session_state.page

if page == 1:
    page_1_intro()
elif page == 2:
    page_2_profile()
elif page == 3:
    page_3_health()
elif page == 4:
    page_2_environment()
elif page == 5:
    page_3_headphone_confirm()
elif page == 6:
    page_4_volume_setup()
elif page == 7:
    page_5_choose_voice()
elif page == 8:
    page_6_instruction()
elif page == 9:
    page_7_main_test()
elif page == 10:
    page_8_result()
