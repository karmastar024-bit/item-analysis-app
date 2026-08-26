import streamlit as st
import tempfile
import math
import pandas as pd
from pathlib import Path
from dataclasses import is_dataclass, asdict

from item_analyzer import ItemAnalyzer


# ============================================================
# PAGE CONFIGURATION
# ============================================================

st.set_page_config(
    page_title="Test Result Helper",
    page_icon="📘",
    layout="wide",
    initial_sidebar_state="collapsed"
)


# ============================================================
# CUSTOM CSS — simple, warm, easy to read
# ============================================================

st.markdown("""
<style>
    html, body, [data-testid="stAppViewContainer"] {
        background-color: #F6F7FA !important;
        color: #1E2A3A !important;
    }

    h1, h2, h3, h4 {
        font-family: 'Segoe UI', sans-serif !important;
    }

    .header-box {
        background-color: #1E4D6B;
        padding: 28px 30px;
        border-radius: 14px;
        color: #FFFFFF;
        margin-bottom: 20px;
    }

    .summary-card {
        background-color: #FFFFFF;
        border: 1px solid #E1E6EE;
        border-radius: 12px;
        padding: 18px 20px;
        text-align: center;
    }

    .summary-number {
        font-size: 30px;
        font-weight: 700;
        color: #1E4D6B;
    }

    .summary-label {
        font-size: 13px;
        color: #5B6B82;
        margin-top: 4px;
    }

    .badge-base {
        display: inline-block;
        padding: 4px 12px;
        border-radius: 20px;
        font-size: 12px;
        font-weight: 700;
    }

    .badge-keep { background-color: #E3F3EA; color: #2F8F5B; }
    .badge-look { background-color: #FBF0DE; color: #C9862B; }
    .badge-fix  { background-color: #FAEAE2; color: #BD5B34; }
    .badge-remove { background-color: #FAE7E5; color: #B23A32; }

    .dist-container {
        display: flex;
        width: 100%;
        height: 28px;
        border-radius: 6px;
        overflow: hidden;
        margin: 10px 0 4px 0;
        border: 1px solid #DEE4EF;
    }

    .dist-segment {
        display: flex;
        align-items: center;
        justify-content: center;
        color: white;
        font-size: 12px;
        font-weight: bold;
    }

    .legend-dot {
        display: inline-block;
        width: 10px;
        height: 10px;
        border-radius: 50%;
        margin-right: 5px;
    }
</style>
""", unsafe_allow_html=True)


# ============================================================
# HEADER
# ============================================================

st.html("""
<div class="header-box">
    <h1 style="color: white; margin: 0 0 8px 0;">📘 Test Result Helper</h1>
    <p style="color: #D6E3ED; font-size: 15px; margin: 0;">
        Upload your answer key and your students' answers. This tool tells you,
        in plain language, which questions worked well and which ones need
        a second look — no statistics background needed.
    </p>
</div>
""")


# ============================================================
# UPLOAD REGION
# ============================================================

st.markdown("### Step 1: Upload your files")

col_key, col_data = st.columns(2)

with col_key:
    st.markdown("**Answer Key** (.xlsx)")
    st.caption("The sheet with the correct answer for each question.")
    key_file = st.file_uploader(
        "Answer key file",
        type=["xlsx", "xls"],
        label_visibility="collapsed"
    )

with col_data:
    st.markdown("**Student Answers** (.xlsx)")
    st.caption("The sheet with each student's ID, name, and answers.")
    data_file = st.file_uploader(
        "Student answers file",
        type=["xlsx", "xls"],
        label_visibility="collapsed"
    )


# ============================================================
# PLAIN-LANGUAGE TRANSLATIONS
# ============================================================

REC_INFO = {
    "RETAIN":  {"label": "Keep as is",        "badge": "badge-keep",   "icon": "✅",
                "advice": "This question is doing its job well. You can reuse it as it is."},
    "REVIEW":  {"label": "Take a look",       "badge": "badge-look",   "icon": "👀",
                "advice": "This question mostly works but is worth a quick review before reusing it."},
    "REVISE":  {"label": "Needs revising",    "badge": "badge-fix",    "icon": "✏️",
                "advice": "This question has a real problem — the wording or answer choices likely need changing."},
    "DISCARD": {"label": "Consider removing", "badge": "badge-remove", "icon": "🗑️",
                "advice": "This question is confusing students in a way that hurts your results — stronger students did worse on it than weaker ones. Consider replacing it."},
}

DIFFICULTY_PLAIN = {
    "Very Difficult": "Too hard — most students got this wrong.",
    "Too Easy": "Too easy — almost everyone got this right.",
    "Ideal": "A good level of difficulty for this class.",
}

DISCRIMINATION_PLAIN = {
    "Negative": "Confusing: your weaker students did BETTER on this question than your stronger students.",
    "Poor": "Not very useful: this question doesn't clearly tell apart strong and weak students.",
    "Good": "Working well: strong students did clearly better than weak students on this question.",
}


def get_value(obj, key, default=None):
    """Safely retrieve a value from dictionaries or objects."""
    if isinstance(obj, dict):
        return obj.get(key, default)
    return getattr(obj, key, default)


def sanitize(data):
    """
    Convert dataclass objects such as ItemStats into dictionaries,
    recursively sanitize nested structures, and replace NaN/Infinity
    with 0.0.
    """
    if is_dataclass(data):
        return sanitize(asdict(data))
    if isinstance(data, dict):
        return {k: sanitize(v) for k, v in data.items()}
    if isinstance(data, (list, tuple)):
        return [sanitize(i) for i in data]
    if isinstance(data, float):
        if math.isnan(data) or math.isinf(data):
            return 0.0
    return data


def as_float(value, default=0.0):
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def as_int(value, default=0):
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def render_summary_card(col, number, label):
    with col:
        st.markdown(
            f"""
            <div class="summary-card">
                <div class="summary-number">{number}</div>
                <div class="summary-label">{label}</div>
            </div>
            """,
            unsafe_allow_html=True
        )


def render_distribution_bar(breakdown, omitted_count, omitted_percentage):
    bar_html = '<div class="dist-container">'
    for opt in breakdown:
        pct = as_float(get_value(opt, "percentage", 0.0))
        opt_label = get_value(opt, "option", "")
        if pct <= 0:
            continue
        is_correct = bool(get_value(opt, "is_correct", False))
        is_functional = bool(get_value(opt, "is_functional", False))
        if is_correct:
            color = "#2F8F5B"
        elif is_functional:
            color = "#2C5F8A"
        else:
            color = "#B23A32"
        display_label = str(opt_label) if pct >= 5 else ""
        bar_html += (
            f'<div class="dist-segment" style="flex: {pct} 0 auto; '
            f'background-color: {color};" title="{opt_label}: {pct:.0f}% of students">'
            f'{display_label}</div>'
        )

    if omitted_count > 0:
        bar_html += (
            f'<div class="dist-segment" style="flex: {omitted_percentage} 0 auto; '
            f'background-color: #92A0BD;" title="Left blank: {omitted_percentage:.0f}%">—</div>'
        )
    bar_html += '</div>'
    st.markdown(bar_html, unsafe_allow_html=True)

    st.markdown(
        """
        <span class="legend-dot" style="background-color:#2F8F5B;"></span> Correct answer &nbsp;&nbsp;
        <span class="legend-dot" style="background-color:#2C5F8A;"></span> Wrong answer (chosen by some students) &nbsp;&nbsp;
        <span class="legend-dot" style="background-color:#B23A32;"></span> Wrong answer (barely/never chosen) &nbsp;&nbsp;
        <span class="legend-dot" style="background-color:#92A0BD;"></span> Left blank
        """,
        unsafe_allow_html=True
    )


def get_correct_answer(item):
    """The answer key doesn't ship as its own field on an item — pull it
    from whichever option in the breakdown is flagged as correct."""
    for opt in get_value(item, "option_breakdown", []) or []:
        if bool(get_value(opt, "is_correct", False)):
            return get_value(opt, "option", "")
    return ""


def create_excel_report(summary, items, students):
    """Build a shareable Excel workbook: one plain-language overview
    sheet for quick reading, plus the full numbers for anyone (e.g. an
    exam board or head teacher) who wants the underlying detail."""

    # ---- Sheet 1: Class Summary ----
    summary_df = pd.DataFrame([{
        "Total Students": as_int(get_value(summary, "total_students", 0)),
        "Total Questions": as_int(get_value(summary, "total_questions", 0)),
        "Average Score": round(as_float(get_value(summary, "mean_score", 0)), 2),
        "Average Percentage": round(as_float(get_value(summary, "mean_percentage", 0)), 2),
        "Pass Rate (%)": round(as_float(get_value(summary, "pass_rate", 0)), 2),
        "Highest Score": as_int(get_value(summary, "max_score", 0)),
        "Lowest Score": as_int(get_value(summary, "min_score", 0)),
    }])

    # ---- Sheet 2: Questions Overview (plain language + the numbers) ----
    question_rows = []
    for item in items:
        rec_key = str(get_value(item, "recommendation", "")).upper()
        rec = REC_INFO.get(rec_key, REC_INFO["REVIEW"])
        diff_status = get_value(item, "difficulty_status", "")
        disc_status = get_value(item, "discrimination_status", "")
        nfd = get_value(item, "non_functional_distractors", []) or []

        question_rows.append({
            "Question": get_value(item, "question", ""),
            "Correct Answer": get_correct_answer(item),
            "What to do": rec["label"],
            "Why": rec["advice"],
            "% Got it Right": round(as_float(get_value(item, "difficulty", 0)) * 100, 1),
            "Difficulty": diff_status,
            "Tells apart strong/weak students?": disc_status,
            "Discrimination Index": round(as_float(get_value(item, "discrimination", 0)), 3),
            "Answer choices nobody picked": ", ".join(str(x) for x in nfd) if nfd else "None",
            "Left Blank (%)": round(as_float(get_value(item, "omitted_percentage", 0)), 1),
        })
    questions_df = pd.DataFrame(question_rows)

    # ---- Sheet 3: Answer Choices (per option, per question) ----
    option_rows = []
    for item in items:
        question = get_value(item, "question", "")
        for opt in get_value(item, "option_breakdown", []) or []:
            option_rows.append({
                "Question": question,
                "Option": get_value(opt, "option", ""),
                "Students who chose it": get_value(opt, "count", 0),
                "Percentage": round(as_float(get_value(opt, "percentage", 0)), 1),
                "Correct Answer?": "Yes" if get_value(opt, "is_correct", False) else "No",
                "Worked as a distractor?": (
                    "N/A (correct answer)" if get_value(opt, "is_correct", False)
                    else ("Yes" if get_value(opt, "is_functional", False) else "No — nobody picked it")
                ),
            })
    options_df = pd.DataFrame(option_rows)

    # ---- Sheet 4: Student Results ----
    student_rows = []
    for s in students:
        student_rows.append({
            "Rank": get_value(s, "rank", ""),
            "Student ID": get_value(s, "student_id", ""),
            "Name": get_value(s, "name", ""),
            "Score": get_value(s, "score", 0),
            "Percentage": round(as_float(get_value(s, "percentage", 0)), 2),
        })
    student_df = pd.DataFrame(student_rows)

    output = tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx")
    output.close()

    with pd.ExcelWriter(output.name, engine="openpyxl") as writer:
        summary_df.to_excel(writer, sheet_name="Class Summary", index=False)
        questions_df.to_excel(writer, sheet_name="Questions Overview", index=False)
        options_df.to_excel(writer, sheet_name="Answer Choices", index=False)
        student_df.to_excel(writer, sheet_name="Student Results", index=False)

        for worksheet in writer.book.worksheets:
            worksheet.freeze_panes = "A2"
            for column in worksheet.columns:
                max_length = 0
                column_letter = column[0].column_letter
                for cell in column:
                    try:
                        max_length = max(max_length, len(str(cell.value)))
                    except Exception:
                        pass
                worksheet.column_dimensions[column_letter].width = min(max_length + 3, 50)

    return output.name


def render_question_card(item, expanded=False):
    q_text = get_value(item, "question", "Question")
    rec_key = str(get_value(item, "recommendation", "REVIEW")).upper()
    rec = REC_INFO.get(rec_key, REC_INFO["REVIEW"])

    diff_status = get_value(item, "difficulty_status", "N/A")
    diff_val = as_float(get_value(item, "difficulty", 0.0)) * 100
    disc_status = get_value(item, "discrimination_status", "N/A")

    header = (
        f"{rec['icon']} **{q_text}** — {rec['label']}  "
        f"·  {diff_val:.0f}% of students got it right"
    )

    with st.expander(header, expanded=expanded):
        st.markdown(
            f'<span class="badge-base {rec["badge"]}">{rec["label"].upper()}</span>',
            unsafe_allow_html=True
        )
        st.write(rec["advice"])

        st.markdown("---")

        c1, c2 = st.columns(2)
        with c1:
            st.markdown("**How hard was it?**")
            st.write(DIFFICULTY_PLAIN.get(diff_status, diff_status))
            st.caption(f"{diff_val:.0f}% of students answered correctly.")
        with c2:
            st.markdown("**Did it tell apart strong and weak students?**")
            st.write(DISCRIMINATION_PLAIN.get(disc_status, disc_status))

        non_functional = get_value(item, "non_functional_distractors", []) or []
        if non_functional:
            st.markdown("---")
            st.markdown("**Answer choices nobody picked**")
            st.write(
                f"Options {', '.join(str(x) for x in non_functional)} were barely or never "
                "chosen by students. They aren't fooling anyone — consider rewriting or "
                "replacing them next time you use this question."
            )

        st.markdown("---")
        st.markdown("**What students chose**")

        breakdown = get_value(item, "option_breakdown", []) or []
        omitted_count = as_int(get_value(item, "omitted_count", 0))
        omitted_percentage = as_float(get_value(item, "omitted_percentage", 0.0))
        render_distribution_bar(breakdown, omitted_count, omitted_percentage)


# ============================================================
# RUN ANALYSIS
# ============================================================

if key_file and data_file:

    if st.button("🚀 Analyze My Test", type="primary", use_container_width=True):

        with st.spinner("Reading your files and working out the results..."):
            try:
                with tempfile.TemporaryDirectory() as tmp_dir:
                    tmp_path = Path(tmp_dir)
                    key_path = tmp_path / "key.xlsx"
                    data_path = tmp_path / "data.xlsx"
                    key_path.write_bytes(key_file.getvalue())
                    data_path.write_bytes(data_file.getvalue())

                    analyzer = ItemAnalyzer()
                    raw_results = analyzer.run_analysis(str(key_path), str(data_path))

                results = sanitize(raw_results)
                summary = get_value(results, "summary", {})
                items = get_value(results, "items", []) or []
                students = get_value(results, "students", []) or []

                if not isinstance(items, list):
                    items = list(items)
                if not isinstance(students, list):
                    students = list(students)

                # ----------------------------------------------------
                # CLASS SUMMARY
                # ----------------------------------------------------

                st.markdown("### Step 2: Your class at a glance")

                mean_pct = as_float(get_value(summary, "mean_percentage", 0.0))
                pass_rate = as_float(get_value(summary, "pass_rate", 0.0))
                total_students = as_int(get_value(summary, "total_students", 0))
                total_questions = as_int(get_value(summary, "total_questions", 0))

                s1, s2, s3, s4 = st.columns(4)
                render_summary_card(s1, total_students, "Students")
                render_summary_card(s2, total_questions, "Questions")
                render_summary_card(s3, f"{mean_pct:.0f}%", "Average score")
                render_summary_card(s4, f"{pass_rate:.0f}%", "Passed (≥ 50%)")

                # ----------------------------------------------------
                # QUESTIONS THAT NEED ATTENTION FIRST
                # ----------------------------------------------------

                st.markdown("### Step 3: Questions to look at first")
                st.caption(
                    "These are sorted so the questions needing the most attention appear first."
                )

                priority_order = {"DISCARD": 0, "REVISE": 1, "REVIEW": 2, "RETAIN": 3}
                sorted_items = sorted(
                    items,
                    key=lambda it: priority_order.get(
                        str(get_value(it, "recommendation", "REVIEW")).upper(), 2
                    )
                )

                needs_attention = [
                    it for it in sorted_items
                    if str(get_value(it, "recommendation", "")).upper() in ("DISCARD", "REVISE", "REVIEW")
                ]
                working_well = [
                    it for it in sorted_items
                    if str(get_value(it, "recommendation", "")).upper() == "RETAIN"
                ]

                if needs_attention:
                    for item in needs_attention:
                        render_question_card(item, expanded=False)
                else:
                    st.success("Great news — every question is performing well!")

                if working_well:
                    with st.expander(f"✅ {len(working_well)} question(s) already working well"):
                        for item in working_well:
                            render_question_card(item, expanded=False)

                # ----------------------------------------------------
                # STUDENT RESULTS
                # ----------------------------------------------------

                if students:
                    st.markdown("### Step 4: Student results")
                    table_rows = []
                    for s in students:
                        table_rows.append({
                            "Rank": get_value(s, "rank", ""),
                            "ID": get_value(s, "student_id", ""),
                            "Name": get_value(s, "name", ""),
                            "Score": get_value(s, "score", ""),
                            "Percentage": f"{as_float(get_value(s, 'percentage', 0.0)):.0f}%",
                        })
                    st.dataframe(table_rows, use_container_width=True, hide_index=True)

                # ----------------------------------------------------
                # DOWNLOAD REPORT
                # ----------------------------------------------------

                st.markdown("### Step 5: Download a report to keep or share")
                st.caption(
                    "An Excel file with your class summary, a plain-language "
                    "breakdown of every question, and each student's results — "
                    "useful for your records or to share with your school."
                )

                report_path = create_excel_report(summary, items, students)
                with open(report_path, "rb") as report_file:
                    st.download_button(
                        label="📥 Download Excel Report",
                        data=report_file.read(),
                        file_name="Test_Result_Report.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        type="primary",
                        use_container_width=True
                    )

            except Exception as e:
                st.error(f"Something went wrong while reading your files: {e}")
                with st.expander("Technical details (for troubleshooting)"):
                    st.exception(e)

else:
    st.info(
        "👆 Upload both your Answer Key and your Student Answers spreadsheets above, "
        "then click **Analyze My Test** to see the results."
    )
