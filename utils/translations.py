"""Translation resources. Add a language by adding a new top-level key
(e.g. "es") and registering it in LANGUAGES. Any missing key falls back
to English, so a partial translation never breaks the app.

NOTE: Dzongkha strings below are a starter set and should be reviewed
by a native speaker before wider release."""
import streamlit as st

LANGUAGES = {"en": "English", "dz": "རྫོང་ཁ (Dzongkha)"}
# Future: "es": "Español", "fr": "Français", "hi": "हिन्दी"

STRINGS = {
    "en": {
        "app_title": "ITEM ANALYZER",
        "subtitle": "Made for Educators in Bhutan",
        "language": "Language", "menu": "Menu",
        "welcome": "Welcome to the Item Analyzer",
        "welcome_text": ("Item Analyzer helps educators evaluate the quality of assessment "
                         "items and make evidence-based decisions about which to retain, "
                         "review, revise or discard."),
        "sec_about": "About item analysis", "sec_decision": "How is the decision made?",
        "sec_choose": "What type of item do you want to analyze?",
        "sec_dist": "Test distribution", "btn_dist": "Conduct Test Distribution",
        "mcq": "MCQ", "tf": "True or False", "fill": "Fill in the Blanks",
        "matching": "Matching", "written": "Long / Essay",
        "selected": "Selected-response", "short_cr": "Short constructed-response",
        "written_cr": "Written constructed-response",
        "home": "Home", "about": "About", "how": "How It Works",
        "guide": "Item Analysis Guide", "rules": "Decision Rules",
        "stat_tests": "Statistical Tests", "data_format": "Data Format Guide",
        "samples": "Sample Data", "contact": "Contact",
        "feedback": "Feedback / Report an Issue", "methodology": "Methodology",
        "run": "Run analysis", "download": "Download results",
        "footer_created": "Created by Karma Dorji",
        "footer_tool": "Item Analyzer • Educational Assessment Tool",
        "footer_mission": "Designed to support educators in making evidence-based assessment decisions.",
        "privacy": ("🔒 Privacy: uploaded files are processed in memory for your current "
                    "session only. They are not saved, and no student data is sent to any "
                    "external service. Please use student ID numbers, not names."),
    },
    "dz": {
        "language": "སྐད་ཡིག", "menu": "དཀར་ཆག",
    },
}


def current_lang():
    return st.session_state.get("lang", "en")


def t(key, lang=None):
    lang = lang or current_lang()
    return STRINGS.get(lang, {}).get(key) or STRINGS["en"].get(key, key)
