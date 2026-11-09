"""MCQ upload workflow, using the shared item-page layout."""
import hashlib
from pathlib import Path

import streamlit as st

from utils.mcq_workbook import analyze_mcq_workbook
from utils.translations import t

TEMPLATE = Path(__file__).resolve().parent.parent / "templates" / "mcq_template.xlsx"


def render_upload(sanitize):
    st.header("MCQ — item analysis")
    st.caption("Selected-response item")
    with st.expander("How is this item type scored?"):
        st.markdown("Each answer is scored **1** if it matches the key (A, B, C or D), "
                    "otherwise **0**. Blank responses score 0.")
        st.markdown("**Total Score** includes MCQ and all other sections and determines "
                    "the upper and lower groups for discrimination. Difficulty, distractor "
                    "analysis and the displayed MCQ score use the MCQ responses.")
    c1, c2 = st.columns([3, 1.4])
    c1.caption("File layout: gold KEY row above Student ID, Name, Total Score, Q1, Q2, … headers. "
               "Keep the sheet named MCQ. Name and overall Total Score are required.")
    c2.download_button("⬇️ Excel template", TEMPLATE.read_bytes(), "MCQ_Template.xlsx",
                       "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                       key="mcq_combined_template", width="stretch")
    st.caption(t("privacy"))

    uploaded = st.file_uploader("Upload .xlsx", type=["xlsx"], key="mcq_combined_upload",
                                help="One completed MCQ workbook, up to 10 MB.")
    sig = hashlib.sha256(uploaded.getvalue()).hexdigest() if uploaded else None
    if st.session_state.get("mcq_workbook_signature") != sig:
        st.session_state.pop("analysis_results", None)
    st.session_state["mcq_workbook_signature"] = sig
    if uploaded is None:
        st.session_state.pop("analysis_results", None)
        st.info("Upload a file to begin.")
        return

    if st.button("▶ Run analysis", type="primary", key="run_mcq"):
        st.session_state.pop("analysis_results", None)
        try:
            with st.spinner("Checking workbook and analysing responses…"):
                if not uploaded.name.lower().endswith(".xlsx"):
                    raise ValueError("Only .xlsx workbooks are accepted.")
                results = sanitize(analyze_mcq_workbook(uploaded.getvalue()))
                st.session_state["analysis_results"] = results
            st.success("Analysis complete. Your results are below.")
            if results["summary"]["total_students"] < 30:
                st.warning("Fewer than 30 students: treat item decisions as indicative.")
        except ValueError as exc:
            st.error(str(exc))
