import streamlit as st
from components import explanations as ex
from components.navigation import go
from utils.translations import t


def render():
    st.markdown(f"## {t('welcome')}")
    st.write(t("welcome_text"))
    st.caption(t("privacy"))

    st.markdown(f"### 1 · {t('sec_about')}"); ex.render_stat_tabs()
    st.markdown(f"### 2 · {t('sec_decision')}"); ex.render_rule_tabs()

    st.markdown(f"### 3 · {t('sec_choose')}")
    st.caption(f"**{t('selected')}:** MCQ, True/False, Matching  ·  **{t('short_cr')}:** Fill in the Blanks  ·  "
               f"**{t('written_cr')}:** Short Answer, Long Answer, Essay")
    choices = [("mcq", "📝"), ("tf", "✔️"), ("fill", "✏️"), ("matching", "🔗"), ("written", "📄")]
    target = {"mcq": "mcq", "tf": "true_false", "fill": "fill_blank", "matching": "matching", "written": "written"}
    cols = st.columns(5)
    for col, (k, icon) in zip(cols, choices):
        with col:
            st.markdown('<div class="ia-choice">', unsafe_allow_html=True)
            if st.button(f"{icon}\n\n{t(k)}", key=f"choose_{k}", width="stretch"):
                go(target[k])
            st.markdown("</div>", unsafe_allow_html=True)

    st.markdown(f"### 4 · {t('sec_dist')}")
    if st.button("📊 " + t("btn_dist"), type="primary", width="stretch"):
        go("statistics")
