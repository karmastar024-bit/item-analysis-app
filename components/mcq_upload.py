"""Single-workbook upload and guidance for the MCQ page."""
import hashlib
from pathlib import Path

import streamlit as st

from utils.mcq_workbook import analyze_mcq_workbook

TEMPLATE = Path(__file__).resolve().parent.parent / "templates" / "mcq_template.xlsx"


def render_upload(sanitize):
    st.markdown('''
<style>
.mcq-format {overflow-x:auto; border:1px solid #dce3ec; border-radius:12px; margin:16px 0 8px;}
.mcq-format table {width:100%; border-collapse:collapse; font-size:14px; color:#16233e;}
.mcq-format th {background:#203653; color:white; padding:13px 16px; text-align:left; white-space:nowrap;}
.mcq-format td {padding:12px 16px; border-bottom:1px solid #e2e8f0; white-space:nowrap;}
.mcq-format .answer-key td {background:#fff0cc; color:#704800; font-weight:700;}
.mcq-format .student-row td {background:#f4f7fb;}
.mcq-format .student-row td:first-child {color:#245e78; font-weight:600;}
.mcq-format .student-row td:nth-child(3) {background:#e4f2f1; color:#155e59; font-weight:600;}
</style>
<div class="section-intro">
 <div class="section-kicker">MCQ analysis</div>
 <div class="section-title">One workbook. Your complete assessment.</div>
 <p class="section-copy">Keep the answer key, student details, overall scores and MCQ responses together.</p>
</div>
<div class="workflow-steps">
 <div class="workflow-step"><span>1</span>Download the Excel template</div>
 <div class="workflow-step"><span>2</span>Fill in the key and student rows</div>
 <div class="workflow-step"><span>3</span>Upload and analyse</div>
</div>
''', unsafe_allow_html=True)
    with st.container(border=True):
        left, right = st.columns([3, 1.5], vertical_alignment="center")
        with left:
            st.subheader("1. Prepare your workbook")
            st.write("**Student ID · Name · Total Score · Q1 · Q2 · …**")
            st.caption("Total Score = marks from MCQ + all other sections. Enter each student's full test score.")
        with right:
            st.download_button("Download Excel template (.xlsx)", TEMPLATE.read_bytes(),
                               "MCQ_Template.xlsx",
                               "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                               key="mcq_combined_template", width="stretch")
        st.markdown('''<div class="mcq-format"><table>
<tbody><tr class="answer-key"><td>KEY</td><td>Answer key</td><td>—</td><td>A</td><td>C</td><td>B</td><td>…</td></tr>
<tr><th>Student ID</th><th>Name</th><th>Total Score</th><th>Q1</th><th>Q2</th><th>Q3</th><th>…</th></tr>
<tr class="student-row"><td>S001</td><td>Example student 1</td><td>78</td><td>A</td><td>C</td><td>D</td><td>…</td></tr>
<tr class="student-row"><td>S002</td><td>Example student 2</td><td>64</td><td>B</td><td>C</td><td>B</td><td>…</td></tr>
</tbody></table></div>''', unsafe_allow_html=True)
        st.caption("Illustrative entries only. Gold = answer key · Teal = overall test score · Blue = student identifiers.")
        with st.expander("How to fill in the template"):
            st.markdown("""
- Keep the sheet named **MCQ** and the first three headers unchanged.
- Enter one correct answer (**A, B, C or D**) for every question in the gold **KEY** row above the column headers. Leave its Total Score blank.
- Enter one student per row, with a unique **Student ID**, **Name**, and numeric **Total Score**.
- Add or remove question columns as needed, using unique headers **Q1, Q2, Q3, …**. Remove unused question columns entirely.
- Enter **A, B, C or D** for each response. Leave an omitted answer blank; it scores zero.
- Add as many student rows as needed. Completely empty rows are ignored.
""")
    with st.container(border=True):
        st.subheader("2. Upload and analyse")
        uploaded = st.file_uploader("Upload your completed MCQ workbook", type=["xlsx"],
                                    key="mcq_combined_upload", help="One .xlsx workbook, up to 10 MB.")
        st.caption("Files are processed in memory. Student names and IDs are not included in the item-analysis reports.")
        sig = hashlib.sha256(uploaded.getvalue()).hexdigest() if uploaded else None
        if st.session_state.get("mcq_workbook_signature") != sig:
            st.session_state.pop("analysis_results", None)
        st.session_state["mcq_workbook_signature"] = sig
        # Results from the previous two-file workflow must not survive migration.
        if not uploaded:
            st.session_state.pop("analysis_results", None)
        st.info("Discrimination uses the upper and lower 27% ranked by Total Score (all sections). "
                "Difficulty, distractor analysis and the displayed MCQ score use the MCQ responses.")
        if st.button("Run Analysis", type="primary", disabled=uploaded is None, width="stretch"):
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
