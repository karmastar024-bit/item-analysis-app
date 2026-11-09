import streamlit as st
from utils.translations import t, LANGUAGES

PAGES = {}   # filled by app.py: key -> st.Page

MENU_KEYS = ["home", "about", "how", "guide", "rules", "stat_tests",
             "data_format", "samples", "methodology", "contact", "feedback"]

CSS = """<style>
.block-container{padding-top:1.4rem;max-width:1180px}
.ia-title{font-size:30px;font-weight:800;letter-spacing:.04em;color:#1F3A5F;margin:0;line-height:1.1}
.ia-sub{color:#5B6678;font-size:15px;margin:2px 0 0 0}
.ia-card{border:1px solid #DCE3EC;border-radius:12px;padding:16px 18px;background:#fff}
div[data-testid="stButton"]>button[kind="secondary"]{border-radius:12px}
.ia-choice button{min-height:84px;font-size:18px;font-weight:600}
</style>"""


def go(key):
    st.switch_page(PAGES[key])


def header():
    st.markdown(CSS, unsafe_allow_html=True)
    left, lang_col, menu_col = st.columns([6, 2.2, 1.6], vertical_alignment="center")
    with left:
        st.markdown(f'<p class="ia-title">{t("app_title")}</p><p class="ia-sub">{t("subtitle")}</p>',
                    unsafe_allow_html=True)
    with lang_col:
        st.selectbox("🌐 " + t("language"), list(LANGUAGES), key="lang",
                     format_func=LANGUAGES.get, label_visibility="collapsed",
                     help="🌐 " + t("language"))
    with menu_col:
        with st.popover("☰ " + t("menu"), width="stretch"):
            for k in MENU_KEYS:
                if k in PAGES:
                    st.page_link(PAGES[k], label=t(k))
    st.divider()
