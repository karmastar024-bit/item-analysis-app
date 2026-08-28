import html
import math
import tempfile
from dataclasses import asdict, is_dataclass
from enum import Enum
from io import BytesIO
from pathlib import Path

import pandas as pd
import streamlit as st

from item_analyzer import ItemAnalyzer


# ============================================================
# PAGE CONFIGURATION
# ============================================================

st.set_page_config(
    page_title="Item Analysis",
    page_icon="",
    layout="wide",
    initial_sidebar_state="collapsed"
)


# ============================================================
# CUSTOM CSS
# ============================================================

st.markdown(
    """
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

.badge-base {
    display: inline-block;
    padding: 4px 12px;
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
    height: 30px;
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

.report-title {
    font-size: 18px;
    font-weight: 700;
    color: #16233E;
}

.small-muted {
    font-size: 12px;
    color: #65728A;
}

/* ========================================================
   UPLOAD PAGE
   ======================================================== */

.upload-card {
    background: #EEF1F5;
    border-radius: 8px;
    min-height: 122px;
    padding: 18px 16px 14px 16px;
    box-sizing: border-box;
    margin-bottom: 8px;
}

.upload-label {
    color: #29313F;
    font-size: 14px;
    line-height: 1.4;
    margin-bottom: 18px;
}

.upload-meta {
    color: #8992A2;
    font-size: 13px;
}

.upload-instructions {
    background: #DCE8FA;
    border-radius: 8px;
    padding: 14px 16px;
    margin: 8px 0 10px 0;
    color: #0057A8;
}

.instruction-title {
    font-size: 14px;
    line-height: 1.5;
    margin-bottom: 4px;
}

.instruction-text {
    font-size: 13px;
    line-height: 1.55;
    color: #145A9C;
}

.upload-instructions b {
    color: #004E97;
}

</style>
""",
    unsafe_allow_html=True
)


# ============================================================
# HEADER
# ============================================================

st.html(
    """
<div class="header-box">

    <div style="
        font-family: monospace;
        font-size: 11px;
        letter-spacing: 0.1em;
        color: #AFC3DC;
        text-transform: uppercase;
    ">
        ITEM ANALYZER
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
        difficulty, discrimination, and distractor readouts
        for every item.
    </p>

</div>
"""
)


# ============================================================
# HELPER FUNCTIONS
# ============================================================

def sanitize(data):
    """
    Convert dataclasses and Enum values into JSON/Streamlit-safe
    Python objects.

    Also handles NaN and Infinity.
    """

    # IMPORTANT:
    # This fixes the previous:
    # NameError: name 'Enum' is not defined
    if isinstance(data, Enum):
        return data.value

    if is_dataclass(data):

        return sanitize(
            asdict(data)
        )

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

        if math.isnan(data) or math.isinf(data):

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

    if rec == "RETAIN":

        return (
            '<span class="badge-base badge-retain">'
            'RETAIN'
            '</span>'
        )

    if rec == "REVIEW":

        return (
            '<span class="badge-base badge-review">'
            'REVIEW'
            '</span>'
        )

    if rec == "REVISE":

        return (
            '<span class="badge-base badge-revise">'
            'REVISE'
            '</span>'
        )

    if rec == "DISCARD":

        return (
            '<span class="badge-base badge-discard">'
            'DISCARD'
            '</span>'
        )

    return (
        '<span class="badge-base badge-review">'
        f'{html.escape(rec)}'
        '</span>'
    )


# ============================================================
# EXCEL REPORT GENERATOR
# ============================================================

def create_excel_report(results):

    """
    Create a complete downloadable Excel report.

    Sheet order:

    1. Item Analysis
    2. Option Breakdown
    3. Overall Summary
    4. Student Ranking
    """

    output = BytesIO()

    summary = get_value(
        results,
        "summary",
        {}
    )

    items = get_value(
        results,
        "items",
        []
    )

    students = get_value(
        results,
        "students",
        []
    )

    # --------------------------------------------------------
    # ITEM ANALYSIS DATA
    # --------------------------------------------------------

    item_rows = []

    for item in items:

        recommendation = get_value(
            item,
            "recommendation",
            ""
        )

        if isinstance(
            recommendation,
            Enum
        ):

            recommendation = (
                recommendation.value
            )

        nfd = get_value(
            item,
            "non_functional_distractors",
            []
        )

        if nfd is None:
            nfd = []

        item_rows.append({

            "Question":
                get_value(
                    item,
                    "question",
                    ""
                ),

            "Question Number":
                get_value(
                    item,
                    "question_number",
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
                get_value(
                    item,
                    "difficulty",
                    0
                ),

            "Difficulty Status":
                get_value(
                    item,
                    "difficulty_status",
                    ""
                ),

            "Discrimination Index":
                get_value(
                    item,
                    "discrimination",
                    0
                ),

            "Discrimination Status":
                get_value(
                    item,
                    "discrimination_status",
                    ""
                ),

            "Distractor Efficiency (%)":
                get_value(
                    item,
                    "distractor_efficiency",
                    0
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
                get_value(
                    item,
                    "omitted_percentage",
                    0
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

                status = "Correct Answer"

            elif is_functional:

                status = "Functional Distractor"

            else:

                status = "Non-functional Distractor"

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
                    get_value(
                        option,
                        "percentage",
                        0
                    ),

                "Status":
                    status
            })

    option_df = pd.DataFrame(
        option_rows
    )

    # --------------------------------------------------------
    # SUMMARY
    # --------------------------------------------------------

    summary_df = pd.DataFrame({

        "Measure": [

            "Total Students",

            "Total Evaluated Items",

            "Mean Score",

            "Standard Deviation",

            "Minimum Score",

            "Maximum Score",

            "Mean Percentage"
        ],

        "Value": [

            get_value(
                summary,
                "total_students",
                0
            ),

            get_value(
                summary,
                "total_questions",
                0
            ),

            get_value(
                summary,
                "mean_score",
                0
            ),

            get_value(
                summary,
                "std_score",
                0
            ),

            get_value(
                summary,
                "min_score",
                0
            ),

            get_value(
                summary,
                "max_score",
                0
            ),

            get_value(
                summary,
                "mean_percentage",
                0
            )
        ]
    })

    # --------------------------------------------------------
    # STUDENT RANKING
    # --------------------------------------------------------

    student_rows = []

    for student in students:

        student_rows.append({

            "Rank":
                get_value(
                    student,
                    "rank",
                    0
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
                get_value(
                    student,
                    "percentage",
                    0
                )
        })

    student_df = pd.DataFrame(
        student_rows
    )

    # --------------------------------------------------------
    # WRITE EXCEL
    # --------------------------------------------------------

    with pd.ExcelWriter(
        output,
        engine="openpyxl"
    ) as writer:

        item_df.to_excel(
            writer,
            sheet_name="Item Analysis",
            index=False
        )

        option_df.to_excel(
            writer,
            sheet_name="Option Breakdown",
            index=False
        )

        summary_df.to_excel(
            writer,
            sheet_name="Overall Summary",
            index=False
        )

        student_df.to_excel(
            writer,
            sheet_name="Student Ranking",
            index=False
        )

        # ----------------------------------------------------
        # FORMATTING
        # ----------------------------------------------------

        workbook = writer.book

        for worksheet in workbook.worksheets:

            # Freeze first row
            worksheet.freeze_panes = "A2"

            # Auto-size columns
            for column_cells in worksheet.columns:

                max_length = 0

                column_letter = (
                    column_cells[0]
                    .column_letter
                )

                for cell in column_cells:

                    try:

                        cell_length = len(
                            str(
                                cell.value
                            )
                        )

                        max_length = max(
                            max_length,
                            cell_length
                        )

                    except Exception:

                        pass

                worksheet.column_dimensions[
                    column_letter
                ].width = min(
                    max(
                        max_length + 2,
                        12
                    ),
                    40
                )

    output.seek(0)

    return output.getvalue()


# ============================================================
# FILE UPLOAD
# ============================================================

# The upload page intentionally starts with two simple cards, matching
# the visual structure in the reference screenshot. Clicking an Upload
# button reveals the appropriate instructions, template download and
# file picker.

TEMPLATE_DIR = Path(__file__).resolve().parent / "templates"
ANSWER_KEY_TEMPLATE = TEMPLATE_DIR / "answer_key_template.xlsx"
STUDENT_RESPONSE_TEMPLATE = TEMPLATE_DIR / "student_response_template.xlsx"


# ------------------------------------------------------------
# SESSION STATE
# ------------------------------------------------------------

if "show_answer_key_upload" not in st.session_state:
    st.session_state["show_answer_key_upload"] = False

if "show_student_upload" not in st.session_state:
    st.session_state["show_student_upload"] = False


# ------------------------------------------------------------
# TEMPLATE DOWNLOAD HELPER
# ------------------------------------------------------------

def template_download_button(
    template_path,
    file_name,
    button_key
):
    """Render a Streamlit download button for a template file."""

    if not template_path.exists():
        st.warning(
            f"Template file not found: {file_name}"
        )
        return

    with open(template_path, "rb") as template_file:
        template_bytes = template_file.read()

    st.download_button(
        label=f"📥 Download {file_name}",
        data=template_bytes,
        file_name=file_name,
        mime=(
            "application/vnd.openxmlformats-officedocument."
            "spreadsheetml.sheet"
        ),
        key=button_key,
        use_container_width=False
    )


# ------------------------------------------------------------
# PAGE TITLE
# ------------------------------------------------------------

st.markdown(
    "### 📥 Load Test Data"
)

col_key, col_data = st.columns(2, gap="medium")


# ============================================================
# ANSWER KEY CARD
# ============================================================

with col_key:

    st.markdown(
        "<div class='upload-card'>"
        "<div class='upload-label'>Choose Answer Key Spreadsheet</div>"
        "<div class='upload-meta'>200MB per file • XLSX, XLS</div>"
        "</div>",
        unsafe_allow_html=True
    )

    if st.button(
        "⇧  Upload",
        key="answer_key_upload_button",
        use_container_width=False
    ):
        st.session_state["show_answer_key_upload"] = True

    if st.session_state["show_answer_key_upload"]:

        st.markdown(
            "<div class='upload-instructions'>"
            "<div class='instruction-title'>💡 Please upload your Answer Key.</div>"
            "<div class='instruction-text'>"
            "Your answer key must match the template shown in "
            "<b>answer_key_template</b>. Please download the template "
            "and make sure your Excel file follows the same structure."
            "</div>"
            "</div>",
            unsafe_allow_html=True
        )

        template_download_button(
            ANSWER_KEY_TEMPLATE,
            "answer_key_template.xlsx",
            "download_answer_key_template"
        )

        key_file = st.file_uploader(
            "Upload your Answer Key",
            type=["xlsx", "xls"],
            key="answer_key",
            help="Upload the completed answer_key_template.xlsx file."
        )

    else:
        key_file = None


# ============================================================
# STUDENT RESPONSE CARD
# ============================================================

with col_data:

    st.markdown(
        "<div class='upload-card'>"
        "<div class='upload-label'>Choose Student Responses Spreadsheet</div>"
        "<div class='upload-meta'>200MB per file • XLSX, XLS</div>"
        "</div>",
        unsafe_allow_html=True
    )

    if st.button(
        "⇧  Upload",
        key="student_upload_button",
        use_container_width=False
    ):
        st.session_state["show_student_upload"] = True

    if st.session_state["show_student_upload"]:

        st.markdown(
            "<div class='upload-instructions'>"
            "<div class='instruction-title'>💡 Please upload Student Responses.</div>"
            "<div class='instruction-text'>"
            "Your student response file must match the template shown in "
            "<b>student_response_template</b>. Please download the template "
            "and make sure your Excel file follows the same structure."
            "</div>"
            "</div>",
            unsafe_allow_html=True
        )

        template_download_button(
            STUDENT_RESPONSE_TEMPLATE,
            "student_response_template.xlsx",
            "download_student_response_template"
        )

        data_file = st.file_uploader(
            "Upload your Student Responses",
            type=["xlsx", "xls"],
            key="student_data",
            help="Upload the completed student_response_template.xlsx file."
        )

    else:
        data_file = None


# ------------------------------------------------------------
# STATUS / ANALYSIS ACCESS
# ------------------------------------------------------------

if key_file or data_file:

    uploaded_col1, uploaded_col2 = st.columns(2)

    with uploaded_col1:

        if key_file:
            st.success(
                f"✓ Answer Key selected: {key_file.name}"
            )

    with uploaded_col2:

        if data_file:
            st.success(
                f"✓ Student Responses selected: {data_file.name}"
            )


if key_file and data_file:

    st.markdown("<div style='height: 8px'></div>", unsafe_allow_html=True)

else:

    st.info(
        "💡 Please upload both the Answer Key and Student "
        "Responses Excel files to unlock the analysis dashboard."
    )

# ============================================================
# ANALYSIS
# ============================================================

if key_file and data_file:

    if st.button(
        "Run Analysis",
        type="primary",
        use_container_width=True
    ):

        with st.spinner(
            "Processing analysis files..."
        ):

            try:

                # ====================================================
                # TEMPORARY FILES
                # ====================================================

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

                    # =================================================
                    # ANALYZER
                    # =================================================

                    analyzer = ItemAnalyzer()

                    raw_results = (
                        analyzer.run_analysis(
                            str(key_path),
                            str(data_path)
                        )
                    )

                # ====================================================
                # SANITIZE
                # ====================================================

                results = sanitize(
                    raw_results
                )

                # Store results in session state
                # so they remain available after download.
                st.session_state[
                    "analysis_results"
                ] = results

                st.success(
                    "✅ Analysis completed successfully."
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
# DISPLAY RESULTS
# ============================================================

if (
    "analysis_results"
    in st.session_state
):

    results = st.session_state[
        "analysis_results"
    ]

    # ========================================================
    # GLOBAL SUMMARY
    # ========================================================

    summary = get_value(
        results,
        "summary",
        {}
    )

    st.markdown(
        "### Overall Summary"
    )

    metric_col1, metric_col2, metric_col3 = st.columns(3)

    with metric_col1:

        st.metric(
            "Total Students",
            get_value(
                summary,
                "total_students",
                0
            )
        )

    with metric_col2:

        st.metric(
            "Total Evaluated Items",
            get_value(
                summary,
                "total_questions",
                0
            )
        )

    with metric_col3:

        mean_score = get_value(
            summary,
            "mean_score",
            0
        )

        total_questions = get_value(
            summary,
            "total_questions",
            0
        )

        st.metric(
            "Mean Score",
            f"{float(mean_score):.2f} / {total_questions}"
        )

    # ========================================================
    # SECOND SUMMARY ROW
    # ========================================================

    metric_col4, metric_col5, metric_col6 = st.columns(3)

    with metric_col4:

        st.metric(
            "Standard Deviation",
            f"{float(get_value(summary, 'std_score', 0)):.2f}"
        )

    with metric_col5:

        st.metric(
            "Minimum Score",
            get_value(
                summary,
                "min_score",
                0
            )
        )

    with metric_col6:

        st.metric(
            "Maximum Score",
            get_value(
                summary,
                "max_score",
                0
            )
        )

    # ========================================================
    # DOWNLOAD REPORT
    # ========================================================

    st.markdown("---")

    st.markdown(
        "### 📥 Download Analysis Report"
    )

    report_bytes = create_excel_report(
        results
    )

    st.download_button(
        label="⬇️ Download Complete Item Analysis Report",
        data=report_bytes,
        file_name="Item_Analysis_Report.xlsx",
        mime=(
            "application/vnd.openxmlformats-officedocument."
            "spreadsheetml.sheet"
        ),
        type="primary",
        use_container_width=True
    )

    st.caption(
        "The report contains Item Analysis first, followed by "
        "Option Breakdown, Overall Summary, and Student Ranking."
    )

    # ========================================================
    # ITEM ANALYSIS
    # ========================================================

    st.markdown("---")

    st.markdown(
        "### 🔬 Item-Wise Analysis"
    )

    st.caption(
        "Each question is evaluated individually for difficulty, "
        "discrimination, distractor efficiency, and final recommendation."
    )

    items = get_value(
        results,
        "items",
        []
    )

    if not isinstance(
        items,
        list
    ):

        items = list(items)

    # ========================================================
    # RECOMMENDATION SUMMARY
    # ========================================================

    retain_count = 0
    review_count = 0
    revise_count = 0
    discard_count = 0

    for item in items:

        recommendation = str(
            get_value(
                item,
                "recommendation",
                ""
            )
        ).upper()

        if recommendation == "RETAIN":
            retain_count += 1

        elif recommendation == "REVIEW":
            review_count += 1

        elif recommendation == "REVISE":
            revise_count += 1

        elif recommendation == "DISCARD":
            discard_count += 1

    rec1, rec2, rec3, rec4 = st.columns(4)

    with rec1:
        st.metric(
            "✅ Retain",
            retain_count
        )

    with rec2:
        st.metric(
            "🟡 Review",
            review_count
        )

    with rec3:
        st.metric(
            "🟠 Revise",
            revise_count
        )

    with rec4:
        st.metric(
            "🔴 Discard",
            discard_count
        )

    # ========================================================
    # QUESTION LOOP
    # ========================================================

    for index, item in enumerate(
        items,
        start=1
    ):

        question = get_value(
            item,
            "question",
            f"Question {index}"
        )

        recommendation = get_value(
            item,
            "recommendation",
            "REVIEW"
        )

        recommendation = str(
            recommendation
        ).upper()

        # ----------------------------------------------------
        # EXPANDER
        # ----------------------------------------------------

        with st.expander(
            f"{question} — {recommendation}",
            expanded=False
        ):

            # =================================================
            # RECOMMENDATION
            # =================================================

            st.markdown(
                recommendation_badge(
                    recommendation
                ),
                unsafe_allow_html=True
            )

            st.markdown("")

            # =================================================
            # BASIC ITEM INFORMATION
            # =================================================

            info1, info2, info3 = st.columns(3)

            with info1:

                st.write(
                    f"**Correct Answer:** "
                    f"`{get_value(item, 'correct_answer', '')}`"
                )

            with info2:

                st.write(
                    f"**Correct Responses:** "
                    f"`{get_value(item, 'correct_count', 0)}` "
                    f"/ "
                    f"`{get_value(item, 'total_students', 0)}`"
                )

            with info3:

                st.write(
                    f"**Omitted Responses:** "
                    f"`{get_value(item, 'omitted_count', 0)}` "
                    f""
                )

            # =================================================
            # METRICS
            # =================================================

            st.markdown("---")

            gauge1, gauge2 = st.columns(2)

            # -------------------------------------------------
            # DIFFICULTY
            # -------------------------------------------------

            with gauge1:

                difficulty = get_value(
                    item,
                    "difficulty",
                    0.0
                )

                try:

                    difficulty = float(
                        difficulty
                    )

                except (
                    TypeError,
                    ValueError
                ):

                    difficulty = 0.0

                difficulty_status = get_value(
                    item,
                    "difficulty_status",
                    "N/A"
                )

                st.metric(
                    "Difficulty Index",
                    f"{difficulty:.3f}",
                    delta=str(
                        difficulty_status
                    ),
                    delta_color="off"
                )

                st.progress(
                    max(
                        0.0,
                        min(
                            1.0,
                            difficulty
                        )
                    )
                )

                st.caption(
                    "Proportion of students who answered correctly."
                )

            # -------------------------------------------------
            # DISCRIMINATION
            # -------------------------------------------------

            with gauge2:

                discrimination = get_value(
                    item,
                    "discrimination",
                    0.0
                )

                try:

                    discrimination = float(
                        discrimination
                    )

                except (
                    TypeError,
                    ValueError
                ):

                    discrimination = 0.0

                discrimination_status = get_value(
                    item,
                    "discrimination_status",
                    "N/A"
                )

                st.metric(
                    "Discrimination Index",
                    f"{discrimination:.3f}",
                    delta=str(
                        discrimination_status
                    ),
                    delta_color="off"
                )

                # Convert -1..+1 to 0..1
                normalized_discrimination = (
                    discrimination + 1
                ) / 2

                st.progress(
                    max(
                        0.0,
                        min(
                            1.0,
                            normalized_discrimination
                        )
                    )
                )

                st.caption(
                    "Difference between upper and lower group performance."
                )

            # =================================================
            # DISTRACTOR METRICS
            # =================================================

            st.markdown("---")

            extra1, extra2 = st.columns(2)

            with extra1:

                efficiency = get_value(
                    item,
                    "distractor_efficiency",
                    0.0
                )

                try:

                    efficiency = float(
                        efficiency
                    )

                except (
                    TypeError,
                    ValueError
                ):

                    efficiency = 0.0

                st.metric(
                    "Distractor Efficiency",
                    f"{efficiency:.0f}%"
                )

            with extra2:

                nfd_list = get_value(
                    item,
                    "non_functional_distractors",
                    []
                )

                if nfd_list:

                    st.write(
                        "**Non-functional Distractors:**"
                    )

                    st.error(
                        ", ".join(
                            str(x)
                            for x in nfd_list
                        )
                    )

                else:

                    st.write(
                        "**Non-functional Distractors:**"
                    )

                    st.success(
                        "None"
                    )

            # =================================================
            # RESPONSE DISTRIBUTION
            # =================================================

            st.markdown("---")

            st.markdown(
                "#### Response Distribution"
            )

            breakdown = get_value(
                item,
                "option_breakdown",
                []
            )

            if breakdown is None:

                breakdown = []

            # -------------------------------------------------
            # BAR
            # -------------------------------------------------

            bar_html = (
                '<div class="dist-container">'
            )

            for option in breakdown:

                percentage = get_value(
                    option,
                    "percentage",
                    0
                )

                option_label = get_value(
                    option,
                    "option",
                    ""
                )

                try:

                    percentage = float(
                        percentage
                    )

                except (
                    TypeError,
                    ValueError
                ):

                    percentage = 0.0

                if percentage <= 0:

                    continue

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

                    background = "#2F8F5B"

                elif is_functional:

                    background = "#2C5F8A"

                else:

                    background = "#B23A32"

                label = (
                    str(option_label)
                    if percentage >= 5
                    else ""
                )

                safe_label = html.escape(
                    label
                )

                bar_html += (
                    '<div '
                    'class="dist-segment" '
                    f'style="flex: {percentage} 0 auto; '
                    f'background-color: {background};" '
                    f'title="{safe_label}: '
                    f'{percentage:.1f}%">'
                    f'{safe_label}'
                    '</div>'
                )

            # -------------------------------------------------
            # OMITTED
            # -------------------------------------------------

            omitted_count = get_value(
                item,
                "omitted_count",
                0
            )

            omitted_percentage = get_value(
                item,
                "omitted_percentage",
                0
            )

            try:

                omitted_count = int(
                    omitted_count
                )

            except (
                TypeError,
                ValueError
            ):

                omitted_count = 0

            try:

                omitted_percentage = float(
                    omitted_percentage
                )

            except (
                TypeError,
                ValueError
            ):

                omitted_percentage = 0.0

            if (
                omitted_count > 0
                and
                omitted_percentage > 0
            ):

                bar_html += (
                    '<div '
                    'class="dist-segment" '
                    f'style="flex: '
                    f'{omitted_percentage} 0 auto; '
                    'background-color: #92A0BD;" '
                    f'title="Omitted: '
                    f'{omitted_percentage:.1f}%">'
                    '—'
                    '</div>'
                )

            bar_html += "</div>"

            st.markdown(
                bar_html,
                unsafe_allow_html=True
            )

            # =================================================
            # OPTION TABLE
            # =================================================

            st.markdown(
                "#### Option Breakdown"
            )

            grid_data = []

            for option in breakdown:

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

                    role = "✅ Correct Answer"

                elif is_functional:

                    role = "✓ Functional Distractor"

                else:

                    role = "❌ Non-functional Distractor"

                percentage = get_value(
                    option,
                    "percentage",
                    0
                )

                try:

                    percentage = float(
                        percentage
                    )

                except (
                    TypeError,
                    ValueError
                ):

                    percentage = 0.0

                grid_data.append({

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

                    "Distribution":
                        f"{percentage:.1f}%",

                    "Diagnostic Evaluation":
                        role
                })

            if grid_data:

                st.table(
                    grid_data
                )

            else:

                st.info(
                    "No option breakdown data was returned."
                )

    # ========================================================
    # FINAL RECOMMENDATION SUMMARY
    # ========================================================

    st.markdown("---")

    st.markdown(
        "### Item Recommendation Summary"
    )

    recommendation_rows = []

    for item in items:

        recommendation = str(
            get_value(
                item,
                "recommendation",
                ""
            )
        ).upper()

        recommendation_rows.append({

            "Question":
                get_value(
                    item,
                    "question",
                    ""
                ),

            "Difficulty":
                f"{float(get_value(item, 'difficulty', 0)):.3f}",

            "Difficulty Status":
                get_value(
                    item,
                    "difficulty_status",
                    ""
                ),

            "Discrimination":
                f"{float(get_value(item, 'discrimination', 0)):.3f}",

            "Discrimination Status":
                get_value(
                    item,
                    "discrimination_status",
                    ""
                ),

            "Distractor Efficiency":
                f"{float(get_value(item, 'distractor_efficiency', 0)):.0f}%",

            "Recommendation":
                recommendation
        })

    if recommendation_rows:

        st.dataframe(
            pd.DataFrame(
                recommendation_rows
            ),
            use_container_width=True,
            hide_index=True
        )


