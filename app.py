"""ITEM ANALYZER – entry point / router.
Each page is either a callable in pages/ or (MCQ) the original script."""
import streamlit as st

st.set_page_config(page_title="Item Analyzer", page_icon="📘", layout="wide",
                   initial_sidebar_state="collapsed")

from components import navigation
from components.footer import footer
from pages import (home, true_false, fill_blank, matching, written_response,
                   score_statistics, guides)

P = st.Page
pages = {
    "home": P(home.render, title="Home", icon="🏠", url_path="home", default=True),
    "mcq": P("pages/mcq.py", title="MCQ", icon="📝", url_path="mcq"),
    "true_false": P(true_false.render, title="True or False", icon="✔️", url_path="true-false"),
    "fill_blank": P(fill_blank.render, title="Fill in the Blanks", icon="✏️", url_path="fill-blank"),
    "matching": P(matching.render, title="Matching", icon="🔗", url_path="matching"),
    "written": P(written_response.render, title="Written / Essay", icon="📄", url_path="written"),
    "statistics": P(score_statistics.render, title="Test Distribution", icon="📊", url_path="test-distribution"),
    "about": P(guides.about, title="About", url_path="about"),
    "how": P(guides.how_it_works, title="How It Works", url_path="how-it-works"),
    "guide": P(guides.item_guide, title="Item Analysis Guide", url_path="item-analysis-guide"),
    "rules": P(guides.decision_rules, title="Decision Rules", url_path="decision-rules"),
    "stat_tests": P(guides.statistical_tests_guide, title="Statistical Tests", url_path="statistical-tests"),
    "methodology": P(guides.methodology, title="Methodology", url_path="methodology"),
    "data_format": P(guides.data_format, title="Data Format Guide", url_path="data-format"),
    "samples": P(guides.sample_data, title="Sample Data", url_path="sample-data"),
    "contact": P(guides.contact, title="Contact", url_path="contact"),
    "feedback": P(guides.feedback, title="Feedback", url_path="feedback"),
}
navigation.PAGES.update(pages)
current = st.navigation(list(pages.values()), position="hidden")
navigation.header()
if current.url_path != "home":
    st.page_link(pages["home"], label="← Home")
current.run()
footer()
