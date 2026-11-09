import streamlit as st
from utils.translations import t, LANGUAGES

PAGES = {}   # filled by app.py: key -> st.Page

MENU_KEYS = ["home", "about", "how", "guide", "rules", "stat_tests",
             "data_format", "samples", "methodology", "contact", "feedback"]

CSS = """<style>
.block-container{padding-top:4.5rem;max-width:1180px}
.ia-title{font-size:30px;font-weight:800;letter-spacing:.04em;color:var(--text-color);margin:0;line-height:1.1}
.ia-sub{color:var(--text-color);opacity:.72;font-size:15px;margin:2px 0 0 0}
.ia-card{border:1px solid #DCE3EC;border-radius:12px;padding:16px 18px;background:#fff}
div[data-testid="stButton"]>button[kind="secondary"]{border-radius:12px}
.ia-choice button{min-height:84px;font-size:18px;font-weight:600}

.stApp {
    background: radial-gradient(ellipse at 8% 10%, #5b9cf522, transparent 50%),
                radial-gradient(ellipse at 92% 50%, #8a62d522, transparent 50%),
                var(--background-color);
}
.ia-card, .ia-footer, [data-testid="stMetric"],
[data-testid="stExpander"], [data-testid="stFileUploaderDropzone"],
[data-testid="stForm"], [data-testid="stVegaLiteChart"] {
    background: color-mix(in srgb, var(--secondary-background-color) 72%, transparent);
    border: 1px solid color-mix(in srgb, var(--text-color) 14%, transparent);
    border-radius: 18px;
    box-shadow: inset 0 1px 0 #ffffff30, 0 8px 28px #1023440a;
    backdrop-filter: blur(18px); -webkit-backdrop-filter: blur(18px);
}
.ia-footer, [data-testid="stMetric"] {padding: 18px;}
[data-testid="stVegaLiteChart"] {padding: 12px;}
[data-testid="stButton"] button, [data-testid="stDownloadButton"] button,
[data-testid="stPopover"] button, [data-baseweb="input"], [data-baseweb="select"] > div,
[data-baseweb="textarea"], [data-baseweb="tab-list"] {
    border-radius: 12px;
    background: color-mix(in srgb, var(--secondary-background-color) 80%, transparent);
    box-shadow: inset 0 1px 0 #ffffff25;
    backdrop-filter: blur(12px); -webkit-backdrop-filter: blur(12px);
}
button:focus-visible {outline: 3px solid #6495ed; outline-offset: 3px;}
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
