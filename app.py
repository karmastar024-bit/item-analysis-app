import streamlit as st
import tempfile
import math
from pathlib import Path
from dataclasses import is_dataclass, asdict
from enum import Enum

from item_analyzer import ItemAnalyzer


# ============================================================
# PAGE CONFIGURATION
# ============================================================

st.set_page_config(
    page_title="Item Analysis Instrument",
    layout="wide",
    initial_sidebar_state="collapsed"
)


# ============================================================
# CUSTOM CSS
# ============================================================

st.markdown("""
<style>

html, body, [data-testid="stAppViewContainer"] {
    background-color: #F3F5F8 !important;
    color: #16233E !important;
}

h1, h2, h3 {
    font-family: 'Space Grotesk', sans-serif !important;
}

.header-box {
    background-color: #16233E;
    background-image:
        linear-gradient(
            rgba(255,255,255,0.04) 1px,
            transparent 1px
        ),
        linear-gradient(
            90deg,
            rgba(255,255,255,0.04) 1px,
            transparent 1px
        );

    background-size: 20px 20px;

    padding: 30px;
    border-radius: 14px;

    color: #FFFFFF;

    margin-bottom: 25px;
}

.badge {
    display: inline-block;
    padding: 5px 12px;
    border-radius: 20px;
    font-size: 11px;
    font-weight: 700;
    text-transform: uppercase;
}

.badge-retain {
    background-color: #E3F3EA;
    color: #2F8F5B;
}

.badge-review {
    background-color: #FBF0DE;
    color: #C9862B;
}

.badge-revise {
    background-color: #FAEAE2;
    color: #BD5B34;
}

.badge-discard {
    background-color: #FAE7E5;
    color: #B23A32;
}

.dist-container {
    display: flex;

    width: 100%;
    height: 28px;

    border-radius: 6px;
    overflow: hidden;

    margin: 10px 0;

    border: 1px solid #DEE4EF;
}

.dist-segment {
    display: flex;

    align-items: center;
    justify-content: center;

    color: white;

    font-family: monospace;
    font-size: 11px;
    font-weight: bold;
}

.summary-card {
    background: white;
    border: 1px solid #DEE4EF;
    border-radius: 10px;
    padding: 15px;
    margin-bottom: 10px;
}

</style>
""", unsafe_allow_html=True)


# ============================================================
# HEADER
# ============================================================

st.html("""
<div class="header-box">

    <div style="
        font-family: monospace;
        font-size: 11px;
        letter-spacing: 0.1em;
        color: #AFC3DC;
        text-transform: uppercase;
    ">
        🎯 ITEM ANALYSIS INSTRUMENT
    </div>

    <h1 style="
        color: white;
        margin: 5px 0;
    ">
        Diagnose your assessment, question by question
    </h1>

    <p style="
        color: #C5D2E6;
        font-size: 14px;
        margin-bottom: 0;
    ">
        Upload an answer key and student responses to calculate
        difficulty, discrimination, and distractor analysis for every item.
    </p>

</div>
""")


# ============================================================
# UPLOAD REGION
# ============================================================

st.markdown("### 📥 Load Test Data")

col_key, col_data = st.columns(2)

with col_key:

    key_file = st.file_uploader(
        "Choose Answer Key Spreadsheet",
        type=["xlsx", "xls"]
    )

with col_data:

    data_file = st.file_uploader(
        "Choose Student Responses Spreadsheet",
        type=["xlsx", "xls"]
    )


# ============================================================
# HELPER FUNCTIONS
# ============================================================

def sanitize(data):

    if is_dataclass(data):

        return sanitize(
            asdict(data)
        )

    if isinstance(data, Enum):

        return data.value

    if isinstance(data, dict):

        return {
            key: sanitize(value)
            for key, value in data.items()
        }

    if isinstance(data, list):

        return [
            sanitize(item)
            for item in data
        ]

    if isinstance(data, tuple):

        return [
            sanitize(item)
            for item in data
        ]

    if isinstance(data, float):

        if (
            math.isnan(data)
            or math.isinf(data)
        ):

            return 0.0

    return data


def get_value(
    obj,
    key,
    default=None
):

    if isinstance(obj, dict):

        return obj.get(
            key,
            default
        )

    return getattr(
        obj,
        key,
        default
    )


def recommendation_badge(
    recommendation
):

    rec = str(
        recommendation
    ).upper()

    if "RETAIN" in rec:

        css = "badge-retain"

    elif "REVIEW" in rec:

        css = "badge-review"

    elif "REVISE" in rec:

        css = "badge-revise"

    else:

        css = "badge-discard"

    return (
        f'<span class="badge {css}">'
        f'{rec}'
        f'</span>'
    )


# ============================================================
# CREATE EXCEL REPORT
# ============================================================

def create_excel_report(
    results
):

    items = get_value(
        results,
        "items",
        []
    )

    summary = get_value(
        results,
        "summary",
        {}
    )

    students = get_value(
        results,
        "students",
        []
    )

    # --------------------------------------------------------
    # ITEM SUMMARY
    # --------------------------------------------------------

    item_rows = []

    for item in items:

        recommendation = get_value(
            item,
            "recommendation",
            ""
        )

        if hasattr(
            recommendation,
            "value"
        ):

            recommendation = (
                recommendation.value
            )

        nfd = get_value(
            item,
            "non_functional_distractors",
            []
        )

        item_rows.append({

            "Question":
                get_value(
                    item,
                    "question",
                    ""
                ),

            "Correct Answer":
                get_value(
                    item,
                    "correct_answer",
                    ""
                ),

            "Correct Count":
                get_value(
                    item,
                    "correct_count",
                    0
                ),

            "Total Students":
                get_value(
                    item,
                    "total_students",
                    0
                ),

            "Difficulty Index":
                round(
                    float(
                        get_value(
                            item,
                            "difficulty",
                            0
                        )
                    ),
                    3
                ),

            "Difficulty Status":
                get_value(
                    item,
                    "difficulty_status",
                    ""
                ),

            "Discrimination Index":
                round(
                    float(
                        get_value(
                            item,
                            "discrimination",
                            0
                        )
                    ),
                    3
                ),

            "Discrimination Status":
                get_value(
                    item,
                    "discrimination_status",
                    ""
                ),

            "Distractor Efficiency (%)":
                round(
                    float(
                        get_value(
                            item,
                            "distractor_efficiency",
                            0
                        )
                    ),
                    1
                ),

            "Non-functional Distractors":
                ", ".join(
                    str(x)
                    for x in nfd
                )
                if nfd
                else "None",

            "Omitted Count":
                get_value(
                    item,
                    "omitted_count",
                    0
                ),

            "Omitted (%)":
                round(
                    float(
                        get_value(
                            item,
                            "omitted_percentage",
                            0
                        )
                    ),
                    1
                ),

            "Recommendation":
                str(
                    recommendation
                ).upper()
        })

    item_df = pd.DataFrame(
        item_rows
    )

    # --------------------------------------------------------
    # OPTION BREAKDOWN
    # --------------------------------------------------------

    option_rows = []

    for item in items:

        question = get_value(
            item,
            "question",
            ""
        )

        breakdown = get_value(
            item,
            "option_breakdown",
            []
        )

        for option in breakdown:

            option_rows.append({

                "Question":
                    question,

                "Option":
                    get_value(
                        option,
                        "option",
                        ""
                    ),

                "Selection Count":
                    get_value(
                        option,
                        "count",
                        0
                    ),

                "Percentage":
                    round(
                        float(
                            get_value(
                                option,
                                "percentage",
                                0
                            )
                        ),
                        1
                    ),

                "Correct Answer":
                    "Yes"
                    if get_value(
                        option,
                        "is_correct",
                        False
                    )
                    else "No",

                "Functional":
                    "Yes"
                    if get_value(
                        option,
                        "is_functional",
                        False
                    )
                    else "No"
            })

    option_df = pd.DataFrame(
        option_rows
    )

    # --------------------------------------------------------
    # RECOMMENDATION SUMMARY
    # --------------------------------------------------------

    recommendation_rows = []

    for item in items:

        recommendation = get_value(
            item,
            "recommendation",
            ""
        )

        if hasattr(
            recommendation,
            "value"
        ):

            recommendation = (
                recommendation.value
            )

        recommendation_rows.append({

            "Question":
                get_value(
                    item,
                    "question",
                    ""
                ),

            "Recommendation":
                str(
                    recommendation
                ).upper(),

            "Reason":
                (
                    f"Difficulty: "
                    f"{float(get_value(item, 'difficulty', 0)):.3f} "
                    f"({get_value(item, 'difficulty_status', '')}); "
                    f"Discrimination: "
                    f"{float(get_value(item, 'discrimination', 0)):.3f} "
                    f"({get_value(item, 'discrimination_status', '')})"
                )
        })

    recommendation_df = pd.DataFrame(
        recommendation_rows
    )

    # --------------------------------------------------------
    # OVERALL SUMMARY
    # --------------------------------------------------------

    summary_df = pd.DataFrame([{

        "Total Students":
            get_value(
                summary,
                "total_students",
                0
            ),

        "Total Questions":
            get_value(
                summary,
                "total_questions",
                0
            ),

        "Mean Score":
            round(
                float(
                    get_value(
                        summary,
                        "mean_score",
                        0
                    )
                ),
                2
            ),

        "Standard Deviation":
            round(
                float(
                    get_value(
                        summary,
                        "std_score",
                        0
                    )
                ),
                2
            ),

        "Minimum Score":
            get_value(
                summary,
                "min_score",
                0
            ),

        "Maximum Score":
            get_value(
                summary,
                "max_score",
                0
            ),

        "Mean Percentage":
            round(
                float(
                    get_value(
                        summary,
                        "mean_percentage",
                        0
                    )
                ),
                2
            )
    }])

    # --------------------------------------------------------
    # STUDENT REPORT
    # --------------------------------------------------------

    student_rows = []

    for student in students:

        student_rows.append({

            "Rank":
                get_value(
                    student,
                    "rank",
                    ""
                ),

            "Student ID":
                get_value(
                    student,
                    "student_id",
                    ""
                ),

            "Name":
                get_value(
                    student,
                    "name",
                    ""
                ),

            "Score":
                get_value(
                    student,
                    "score",
                    0
                ),

            "Percentage":
                round(
                    float(
                        get_value(
                            student,
                            "percentage",
                            0
                        )
                    ),
                    2
                )
        })

    student_df = pd.DataFrame(
        student_rows
    )

    # --------------------------------------------------------
    # WRITE EXCEL
    # --------------------------------------------------------

    output = (
        tempfile.NamedTemporaryFile(
            delete=False,
            suffix=".xlsx"
        )
    )

    output.close()

    with pd.ExcelWriter(
        output.name,
        engine="openpyxl"
    ) as writer:

        # IMPORTANT:
        # Item analysis comes first

        item_df.to_excel(
            writer,
            sheet_name="Item Analysis",
            index=False
        )

        recommendation_df.to_excel(
            writer,
            sheet_name="Recommendations",
            index=False
        )

        option_df.to_excel(
            writer,
            sheet_name="Option Analysis",
            index=False
        )

        summary_df.to_excel(
            writer,
            sheet_name="Overall Summary",
            index=False
        )

        student_df.to_excel(
            writer,
            sheet_name="Student Scores",
            index=False
        )

        # ----------------------------------------------------
        # Basic formatting
        # ----------------------------------------------------

        workbook = writer.book

        for worksheet in workbook.worksheets:

            worksheet.freeze_panes = "A2"

            for column in worksheet.columns:

                max_length = 0

                column_letter = (
                    column[0].column_letter
                )

                for cell in column:

                    try:

                        length = len(
                            str(cell.value)
                        )

                        if length > max_length:
                            max_length = length

                    except Exception:
                        pass

                worksheet.column_dimensions[
                    column_letter
                ].width = min(
                    max_length + 3,
                    45
                )

    return output.name


# ============================================================
# RUN ANALYSIS
# ============================================================

if key_file and data_file:

    if st.button(
        "🚀 Run Analysis Engine",
        type="primary",
        use_container_width=True
    ):

        with st.spinner(
            "Processing analysis files..."
        ):

            try:

                # ------------------------------------------------
                # TEMPORARY INPUT FILES
                # ------------------------------------------------

                with tempfile.TemporaryDirectory() as tmp_dir:

                    tmp_path = Path(
                        tmp_dir
                    )

                    key_path = (
                        tmp_path
                        / "key.xlsx"
                    )

                    data_path = (
                        tmp_path
                        / "data.xlsx"
                    )

                    key_path.write_bytes(
                        key_file.getvalue()
                    )

                    data_path.write_bytes(
                        data_file.getvalue()
                    )

                    # ------------------------------------------------
                    # ANALYSIS ENGINE
                    # ------------------------------------------------

                    analyzer = (
                        ItemAnalyzer()
                    )

                    raw_results = (
                        analyzer.run_analysis(
                            str(key_path),
                            str(data_path)
                        )
                    )

                # ------------------------------------------------
                # SANITIZE
                # ------------------------------------------------

                results = sanitize(
                    raw_results
                )

                # ====================================================
                # ITEM-WISE ANALYSIS
                # ====================================================

                st.markdown(
                    "## 🔬 Item-Wise Analysis Report"
                )

                st.caption(
                    "Each question is evaluated independently for "
                    "difficulty, discrimination, distractor quality, "
                    "and final recommendation."
                )

                items = get_value(
                    results,
                    "items",
                    []
                )

                # ------------------------------------------------
                # RECOMMENDATION OVERVIEW
                # ------------------------------------------------

                counts = {
                    "RETAIN": 0,
                    "REVIEW": 0,
                    "REVISE": 0,
                    "DISCARD": 0
                }

                for item in items:

                    rec = str(
                        get_value(
                            item,
                            "recommendation",
                            ""
                        )
                    ).upper()

                    if rec in counts:

                        counts[rec] += 1

                r1, r2, r3, r4 = st.columns(4)

                with r1:
                    st.metric(
                        "✅ Retain",
                        counts["RETAIN"]
                    )

                with r2:
                    st.metric(
                        "⚠️ Review",
                        counts["REVIEW"]
                    )

                with r3:
                    st.metric(
                        "🔧 Revise",
                        counts["REVISE"]
                    )

                with r4:
                    st.metric(
                        "❌ Discard",
                        counts["DISCARD"]
                    )

                st.markdown("---")

                # ====================================================
                # QUESTION CARDS
                # ====================================================

                for idx, item in enumerate(
                    items
                ):

                    q_text = get_value(
                        item,
                        "question",
                        f"Q{idx + 1}"
                    )

                    correct_answer = get_value(
                        item,
                        "correct_answer",
                        ""
                    )

                    recommendation = str(
                        get_value(
                            item,
                            "recommendation",
                            "REVIEW"
                        )
                    ).upper()

                    with st.expander(
                        f"📦 {q_text} — {recommendation}",
                        expanded=False
                    ):

                        # --------------------------------------------
                        # Recommendation
                        # --------------------------------------------

                        st.markdown(
                            recommendation_badge(
                                recommendation
                            ),
                            unsafe_allow_html=True
                        )

                        st.markdown("")

                        # --------------------------------------------
                        # Basic item information
                        # --------------------------------------------

                        info1, info2, info3 = st.columns(3)

                        with info1:

                            st.write(
                                "**Question:**"
                            )

                            st.write(
                                q_text
                            )

                        with info2:

                            st.write(
                                "**Correct Answer:**"
                            )

                            st.write(
                                f"### {correct_answer}"
                            )

                        with info3:

                            st.write(
                                "**Recommendation:**"
                            )

                            st.markdown(
                                recommendation_badge(
                                    recommendation
                                ),
                                unsafe_allow_html=True
                            )

                        st.markdown("---")

                        # ============================================
                        # METRICS
                        # ============================================

                        g1, g2, g3 = st.columns(3)

                        # --------------------------------------------
                        # Difficulty
                        # --------------------------------------------

                        with g1:

                            diff_val = float(
                                get_value(
                                    item,
                                    "difficulty",
                                    0
                                )
                            )

                            diff_status = (
                                get_value(
                                    item,
                                    "difficulty_status",
                                    "N/A"
                                )
                            )

                            st.metric(
                                "Difficulty Index",
                                f"{diff_val:.3f}"
                            )

                            st.caption(
                                diff_status
                            )

                            st.progress(
                                max(
                                    0,
                                    min(
                                        1,
                                        diff_val
                                    )
                                )
                            )

                        # --------------------------------------------
                        # Discrimination
                        # --------------------------------------------

                        with g2:

                            disc_val = float(
                                get_value(
                                    item,
                                    "discrimination",
                                    0
                                )
                            )

                            disc_status = (
                                get_value(
                                    item,
                                    "discrimination_status",
                                    "N/A"
                                )
                            )

                            st.metric(
                                "Discrimination Index",
                                f"{disc_val:.3f}"
                            )

                            st.caption(
                                disc_status
                            )

                            norm_disc = (
                                disc_val + 1
                            ) / 2

                            st.progress(
                                max(
                                    0,
                                    min(
                                        1,
                                        norm_disc
                                    )
                                )
                            )

                        # --------------------------------------------
                        # Distractor efficiency
                        # --------------------------------------------

                        with g3:

                            efficiency = float(
                                get_value(
                                    item,
                                    "distractor_efficiency",
                                    0
                                )
                            )

                            st.metric(
                                "Distractor Efficiency",
                                f"{efficiency:.0f}%"
                            )

                            nfd = get_value(
                                item,
                                "non_functional_distractors",
                                []
                            )

                            if nfd:

                                st.caption(
                                    "NFDs: "
                                    + ", ".join(
                                        str(x)
                                        for x in nfd
                                    )
                                )

                            else:

                                st.caption(
                                    "No non-functional distractors"
                                )

                        # ============================================
                        # RESPONSE DISTRIBUTION
                        # ============================================

                        st.markdown(
                            "#### 📊 Response Distribution"
                        )

                        breakdown = get_value(
                            item,
                            "option_breakdown",
                            []
                        )

                        bar_html = (
                            '<div class="dist-container">'
                        )

                        for option in breakdown:

                            pct = float(
                                get_value(
                                    option,
                                    "percentage",
                                    0
                                )
                            )

                            label = str(
                                get_value(
                                    option,
                                    "option",
                                    ""
                                )
                            )

                            is_correct = bool(
                                get_value(
                                    option,
                                    "is_correct",
                                    False
                                )
                            )

                            is_functional = bool(
                                get_value(
                                    option,
                                    "is_functional",
                                    False
                                )
                            )

                            if pct <= 0:
                                continue

                            if is_correct:

                                background = "#2F8F5B"

                            elif is_functional:

                                background = "#2C5F8A"

                            else:

                                background = "#B23A32"

                            display_label = (
                                label
                                if pct >= 5
                                else ""
                            )

                            bar_html += (
                                '<div '
                                'class="dist-segment" '
                                f'style="flex:{pct};'
                                f'background-color:{background};" '
                                f'title="{label}: {pct:.1f}%">'
                                f'{display_label}'
                                '</div>'
                            )

                        omitted_pct = float(
                            get_value(
                                item,
                                "omitted_percentage",
                                0
                            )
                        )

                        if omitted_pct > 0:

                            bar_html += (
                                '<div '
                                'class="dist-segment" '
                                f'style="flex:{omitted_pct};'
                                'background-color:#92A0BD;" '
                                f'title="Omitted: {omitted_pct:.1f}%">'
                                '—'
                                '</div>'
                            )

                        bar_html += (
                            "</div>"
                        )

                        st.markdown(
                            bar_html,
                            unsafe_allow_html=True
                        )

                        # ============================================
                        # OPTION TABLE
                        # ============================================

                        st.markdown(
                            "#### Option Breakdown"
                        )

                        option_table = []

                        for option in breakdown:

                            option_label = get_value(
                                option,
                                "option",
                                ""
                            )

                            count = get_value(
                                option,
                                "count",
                                0
                            )

                            percentage = float(
                                get_value(
                                    option,
                                    "percentage",
                                    0
                                )
                            )

                            is_correct = bool(
                                get_value(
                                    option,
                                    "is_correct",
                                    False
                                )
                            )

                            is_functional = bool(
                                get_value(
                                    option,
                                    "is_functional",
                                    False
                                )
                            )

                            if is_correct:

                                status = (
                                    "✅ Correct Answer"
                                )

                            elif is_functional:

                                status = (
                                    "✓ Functional Distractor"
                                )

                            else:

                                status = (
                                    "❌ Non-functional Distractor"
                                )

                            option_table.append({

                                "Option":
                                    option_label,

                                "Selection Count":
                                    count,

                                "Percentage":
                                    f"{percentage:.1f}%",

                                "Status":
                                    status
                            })

                        if option_table:

                            st.dataframe(
                                pd.DataFrame(
                                    option_table
                                ),
                                use_container_width=True,
                                hide_index=True
                            )

                        # ============================================
                        # ITEM INTERPRETATION
                        # ============================================

                        st.markdown(
                            "#### 📝 Item Interpretation"
                        )

                        diff_status = get_value(
                            item,
                            "difficulty_status",
                            ""
                        )

                        disc_status = get_value(
                            item,
                            "discrimination_status",
                            ""
                        )

                        if recommendation == "RETAIN":

                            st.success(
                                f"{q_text} should be RETAINED. "
                                f"The item has {diff_status.lower()} "
                                f"difficulty and {disc_status.lower()} "
                                f"discrimination."
                            )

                        elif recommendation == "REVIEW":

                            st.warning(
                                f"{q_text} should be REVIEWED. "
                                f"Check the item's difficulty "
                                f"({diff_status.lower()}) and/or "
                                f"discrimination "
                                f"({disc_status.lower()}) before "
                                f"using it again."
                            )

                        elif recommendation == "REVISE":

                            st.warning(
                                f"{q_text} should be REVISED. "
                                f"The item has a weakness in "
                                f"difficulty and/or discrimination. "
                                f"Review the stem, correct answer, "
                                f"and distractors."
                            )

                        else:

                            st.error(
                                f"{q_text} should be DISCARDED. "
                                f"The item has negative discrimination "
                                f"and may be functioning incorrectly."
                            )

                # ====================================================
                # DOWNLOAD REPORT
                # ====================================================

                st.markdown("---")

                st.markdown(
                    "## 📥 Download Analysis Report"
                )

                report_path = (
                    create_excel_report(
                        results
                    )
                )

                with open(
                    report_path,
                    "rb"
                ) as report_file:

                    st.download_button(
                        label="📊 Download Complete Item Analysis Report",
                        data=report_file.read(),
                        file_name="Item_Analysis_Report.xlsx",
                        mime=(
                            "application/vnd.openxmlformats-officedocument"
                            ".spreadsheetml.sheet"
                        ),
                        type="primary",
                        use_container_width=True
                    )

                # ====================================================
                # OVERALL SUMMARY
                # ====================================================

                st.markdown("---")

                st.markdown(
                    "## 📊 Overall Test Summary"
                )

                summary = get_value(
                    results,
                    "summary",
                    {}
                )

                c1, c2, c3 = st.columns(3)

                with c1:

                    st.metric(
                        "Total Students",
                        get_value(
                            summary,
                            "total_students",
                            0
                        )
                    )

                with c2:

                    st.metric(
                        "Total Questions",
                        get_value(
                            summary,
                            "total_questions",
                            0
                        )
                    )

                with c3:

                    st.metric(
                        "Mean Score",
                        f"{float(get_value(summary, 'mean_score', 0)):.2f}"
                    )

                c4, c5, c6 = st.columns(3)

                with c4:

                    st.metric(
                        "Standard Deviation",
                        f"{float(get_value(summary, 'std_score', 0)):.2f}"
                    )

                with c5:

                    st.metric(
                        "Minimum Score",
                        get_value(
                            summary,
                            "min_score",
                            0
                        )
                    )

                with c6:

                    st.metric(
                        "Maximum Score",
                        get_value(
                            summary,
                            "max_score",
                            0
                        )
                    )

                st.metric(
                    "Mean Percentage",
                    f"{float(get_value(summary, 'mean_percentage', 0)):.2f}%"
                )

                # ====================================================
                # STUDENT PERFORMANCE
                # ====================================================

                st.markdown(
                    "### 👨‍🎓 Student Performance"
                )

                students = get_value(
                    results,
                    "students",
                    []
                )

                student_rows = []

                for student in students:

                    student_rows.append({

                        "Rank":
                            get_value(
                                student,
                                "rank",
                                ""
                            ),

                        "Student ID":
                            get_value(
                                student,
                                "student_id",
                                ""
                            ),

                        "Name":
                            get_value(
                                student,
                                "name",
                                ""
                            ),

                        "Score":
                            get_value(
                                student,
                                "score",
                                0
                            ),

                        "Percentage":
                            f"{float(get_value(student, 'percentage', 0)):.2f}%"
                    })

                if student_rows:

                    st.dataframe(
                        pd.DataFrame(
                            student_rows
                        ),
                        use_container_width=True,
                        hide_index=True
                    )

            except Exception as e:

                st.error(
                    f"❌ Computational Execution Failure: {e}"
                )

                with st.expander(
                    "🔍 Technical Error Details",
                    expanded=True
                ):

                    st.exception(e)


# ============================================================
# UPLOAD REMINDER
# ============================================================

else:

    st.info(
        "💡 Please upload both your Answer Key and "
        "Student Responses Excel files to unlock "
        "the analysis dashboard."
    )
