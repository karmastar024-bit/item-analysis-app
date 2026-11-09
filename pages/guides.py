"""Information pages reached from the menu."""
from pathlib import Path
import streamlit as st
from components import explanations as ex
from components.navigation import go
from utils.translations import t

DATA = Path(__file__).resolve().parent.parent / "data"
TEMPLATES = Path(__file__).resolve().parent.parent / "templates"
EMAIL, GITHUB = "karmastar024@gmail.com", "https://github.com/karmastar024-bit/item-analysis-app"


def about():
    st.header(t("about"))
    st.write("**Item Analyzer** helps teachers judge the quality of test items using standard "
             "educational-measurement statistics, and explains every result in plain language.")
    st.markdown("**Item types:** Selected-response (MCQ, True/False, Matching) · Short constructed-response "
                "(Fill in the Blanks) · Written constructed-response (Short Answer, Long Answer, Essay).")
    st.markdown("**Author:** Karma Dorji · " + EMAIL)


def how_it_works():
    st.header(t("how"))
    for i, s in enumerate(["Choose an item type on the Home page.",
        "Download the sample file and arrange your data the same way (see Data Format Guide).",
        "Upload your .csv or .xlsx file. The app checks it and tells you about any problem.",
        "Check or edit the answer key / maximum scores.", "Click **Run analysis**.",
        "Read the decision and the reason for every item.", "Download CSV, Excel or PDF.",
        "Optionally open **Test Distribution** for descriptive statistics, t-tests and z-tests."], 1):
        st.markdown(f"**{i}.** {s}")


def item_guide():
    st.header(t("guide")); ex.render_stat_tabs()


def decision_rules():
    st.header(t("rules")); ex.render_rule_tabs()


def statistical_tests_guide():
    st.header(t("stat_tests"))
    for k, (ltx, txt) in ex.TESTS.items():
        with st.expander(k, expanded=False):
            st.latex(ltx); st.write(txt)
    st.info(ex.ASSUMPTIONS)
    if st.button("Open Test Distribution", type="primary"): go("statistics")


def methodology():
    st.header(t("methodology")); ex.render_methodology()


def data_format():
    st.header(t("data_format"))
    st.markdown("""
**Excel templates** — gold KEY (or MAX) row above the column headers:
`Student ID`, `Name`, `Total Score`, `Q1`, `Q2`, … . Enter students below the headers.
Gold marks the key, teal marks Total Score, and blue marks student details.
Files: `.csv` or `.xlsx` (first sheet), max 10 MB. Older files with `StudentID`
and a KEY/MAX row below the headers remain supported.

| Item type | Special row (above headers in Excel templates) | Cell content |
|---|---|---|
| MCQ (.xlsx only) | One KEY row in sheet MCQ; columns Student ID, Name, Total Score, Q1, Q2, … | A, B, C or D |
| True/False | `KEY` row | True/False (or T/F) |
| Fill in the Blanks | `KEY` row | Accepted answers separated by `\\|`, e.g. `Paro\\|Paro Dzong` |
| Matching | `KEY` row | The matching letter/number, e.g. `C` |
| Written | `MAX` row | Maximum score for the item; student cells hold the score awarded |

MCQ requires student names and IDs. Total Score is MCQ + all sections and determines upper/lower discrimination groups.
For other item types, Name and Total Score are optional and are not treated as questions.
Their analysis and student totals use the item responses or awarded scores.

Blank cells = no response (scored 0). Each item must have a key (or maximum score).
""")
    st.code("\n".join((DATA / "sample_fill_blank.csv").read_text(encoding="utf-8").splitlines()[:4]), language="text")
    st.caption("Legacy CSV example (Fill in the Blanks): row 2 is the KEY row. Excel templates put KEY above the headers.")


def sample_data():
    st.header(t("samples"))
    st.write("Fictional data with deliberately weak items so you can see each decision.")
    files = [("MCQ – combined Excel template", TEMPLATES / "mcq_template.xlsx"),
             ("True or False – Excel template", TEMPLATES / "true_false_template.xlsx"),
             ("Fill in the Blanks – Excel template", TEMPLATES / "fill_blank_template.xlsx"),
             ("Matching – Excel template", TEMPLATES / "matching_template.xlsx"),
             ("Written / Essay – Excel template", TEMPLATES / "written_template.xlsx"),
             ("True or False – sample data", DATA / "sample_true_false.csv"),
             ("Fill in the Blanks – sample data", DATA / "sample_fill_blank.csv"),
             ("Matching – sample data", DATA / "sample_matching.csv"),
             ("Written / Essay – sample data", DATA / "sample_written.csv")]
    for label, p in files:
        if p.exists():
            st.download_button(f"⬇️ {label}", p.read_bytes(), p.name, key=f"dl_{p.name}")


def contact():
    st.header(t("contact"))
    st.write(f"**Karma Dorji** · [{EMAIL}](mailto:{EMAIL})")


def feedback():
    st.header(t("feedback"))
    st.write("Found a problem or have an idea? Please do **not** include student data.")
    st.link_button("Report an issue on GitHub", f"{GITHUB}/issues")
    st.link_button("Email feedback", f"mailto:{EMAIL}?subject=Item%20Analyzer%20feedback")
