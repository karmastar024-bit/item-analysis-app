from html import escape
import streamlit as st
from utils.translations import t

VERSION = "2.0.0"
GITHUB = "https://github.com/karmastar024-bit/item-analysis-app"


def footer():
    st.markdown("---")
    st.markdown(
        f"""<div class="ia-footer" style="text-align:center;font-size:13px;line-height:1.7">
        <p>{escape(t("privacy"))}</p>
        {t('footer_created')} · <a href="mailto:karmastar024@gmail.com">karmastar024@gmail.com</a><br>
        {t('footer_tool')}<br>
        <em>{t('footer_mission')}</em><br>
        <span style="font-size:12px">v{VERSION} · <a href="{GITHUB}" target="_blank">GitHub</a> ·
        <a href="{GITHUB}/issues" target="_blank">Feedback</a></span></div>""",
        unsafe_allow_html=True)
