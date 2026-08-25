import streamlit as st
import tempfile
import math
from pathlib import Path
from dataclasses import is_dataclass, asdict

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
        height: 26px;
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
        difficulty, discrimination, and distractor readouts for every item.
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
        "Choose Answer Key Spreadsheet (.xlsx)",
        type=["xlsx", "xls"]
    )

with col_data:
    data_file = st.file_uploader(
        "Choose Student Responses Spreadsheet (.xlsx)",
        type=["xlsx", "xls"]
    )


# ============================================================
# HELPER FUNCTIONS
# ============================================================

def get_status_class(status, block_type="diff"):
    if status in ["Ideal", "Good"]:
        return "good"
    if status in ["Too Easy", "Poor"]:
        return "mid"
    return "poor"


def sanitize(data):
    """
    Convert ItemStats/dataclass objects to dictionaries,
    recursively sanitize nested structures, and replace
    NaN/Infinity with 0.0.
    """

    # Dataclass objects such as ItemStats
    if is_dataclass(data):
        return sanitize(asdict(data))

    # Dictionaries
    if isinstance(data, dict):
        return {
            k: sanitize(v)
            for k, v in data.items()
        }

    # Lists
    if isinstance(data, list):
        return [
            sanitize(i)
            for i in data
        ]

    # Tuples
    if isinstance(data, tuple):
        return [
            sanitize(i)
            for i in data
        ]

    # Floats
    if isinstance(data, float):
        if math.isnan(data) or math.isinf(data):
            return 0.0

    return data


def get_value(obj, key, default=None):
    """
    Safely retrieve a value from dictionaries or objects.

    This provides extra compatibility if ItemAnalyzer returns
    regular objects instead of dictionaries/dataclasses.
    """

    if isinstance(obj, dict):
        return obj.get(key, default)

    return getattr(obj, key, default)


# ============================================================
# RUN COMPUTING ENGINE
# ============================================================

if key_file and data_file:

    if st.button(
        "🚀 Run Analysis Engine",
        type="primary",
        use_container_width=True
    ):

        with st.spinner("Processing analysis files in backend..."):

            try:

                # ----------------------------------------------------
                # Create temporary files
                # ----------------------------------------------------

                with tempfile.TemporaryDirectory() as tmp_dir:

                    tmp_path = Path(tmp_dir)

                    key_path = tmp_path / "key.xlsx"
                    data_path = tmp_path / "data.xlsx"

                    key_path.write_bytes(
                        key_file.getvalue()
                    )

                    data_path.write_bytes(
                        data_file.getvalue()
                    )

                    # ------------------------------------------------
                    # Run analysis engine
                    # ------------------------------------------------

                    analyzer = ItemAnalyzer()

                    raw_results = analyzer.run_analysis(
                        str(key_path),
                        str(data_path)
                    )

                # ----------------------------------------------------
                # Sanitize analyzer output
                # ----------------------------------------------------

                results = sanitize(raw_results)

                # ----------------------------------------------------
                # Global summary
                # ----------------------------------------------------

                summary = get_value(
                    results,
                    "summary",
                    {}
                )

                st.markdown("### 📊 Overall Test Summary")

                metric_col1, metric_col2 = st.columns(2)

                with metric_col1:
                    st.metric(
                        label="Total Students Scaled",
                        value=get_value(
                            summary,
                            "total_students",
                            0
                        )
                    )

                with metric_col2:
                    st.metric(
                        label="Total Evaluated Items",
                        value=get_value(
                            summary,
                            "total_questions",
                            0
                        )
                    )

                # ----------------------------------------------------
                # Per-question analysis
                # ----------------------------------------------------

                st.markdown("### 🔬 Per-Question Analysis")

                st.caption(
                    "Click a question card below to expand its "
                    "full response distribution profile and option breakdowns."
                )

                items = get_value(
                    results,
                    "items",
                    []
                )

                # Safety check
                if not isinstance(items, list):
                    items = list(items) if items else []

                for idx, item in enumerate(items):

                    q_text = get_value(
                        item,
                        "question",
                        f"Question {idx + 1}"
                    )

                    rec = get_value(
                        item,
                        "recommendation",
                        "Review"
                    )

                    if rec is None:
                        rec = "Review"

                    rec = str(rec).lower()

                    # ------------------------------------------------
                    # Question card
                    # ------------------------------------------------

                    with st.expander(
                        f"📦 {q_text} — Recommendation: {rec.upper()}"
                    ):

                        # ============================================
                        # METRIC GAUGES
                        # ============================================

                        g_col1, g_col2 = st.columns(2)

                        # --------------------------------------------
                        # Difficulty
                        # --------------------------------------------

                        with g_col1:

                            diff_val = get_value(
                                item,
                                "difficulty",
                                0.0
                            )

                            diff_status = get_value(
                                item,
                                "difficulty_status",
                                "N/A"
                            )

                            try:
                                diff_val = float(diff_val)
                            except (TypeError, ValueError):
                                diff_val = 0.0

                            st.metric(
                                label="Difficulty Level",
                                value=f"{diff_val:.3f}",
                                delta=str(diff_status),
                                delta_color="off"
                            )

                            st.progress(
                                max(
                                    0.0,
                                    min(
                                        1.0,
                                        diff_val
                                    )
                                )
                            )

                        # --------------------------------------------
                        # Discrimination
                        # --------------------------------------------

                        with g_col2:

                            disc_val = get_value(
                                item,
                                "discrimination",
                                0.0
                            )

                            disc_status = get_value(
                                item,
                                "discrimination_status",
                                "N/A"
                            )

                            try:
                                disc_val = float(disc_val)
                            except (TypeError, ValueError):
                                disc_val = 0.0

                            st.metric(
                                label="Discrimination Power",
                                value=f"{disc_val:.3f}",
                                delta=str(disc_status),
                                delta_color="off"
                            )

                            norm_disc = (
                                disc_val + 1.0
                            ) / 2.0

                            st.progress(
                                max(
                                    0.0,
                                    min(
                                        1.0,
                                        norm_disc
                                    )
                                )
                            )

                        # ============================================
                        # EXTRA METRICS
                        # ============================================

                        st.markdown("---")

                        eff_rate = get_value(
                            item,
                            "distractor_efficiency",
                            0.0
                        )

                        try:
                            eff_rate = float(eff_rate)
                        except (TypeError, ValueError):
                            eff_rate = 0.0

                        nfds_list = get_value(
                            item,
                            "non_functional_distractors",
                            []
                        )

                        if nfds_list is None:
                            nfds_list = []

                        m_col1, m_col2 = st.columns(2)

                        with m_col1:
                            st.write(
                                f"**Distractor Efficiency:** "
                                f"`{eff_rate:.0f}%`"
                            )

                        with m_col2:

                            nfd_string = (
                                ", ".join(
                                    str(x)
                                    for x in nfds_list
                                )
                                if nfds_list
                                else "None"
                            )

                            st.write(
                                f"**Flagged NFDs:** "
                                f"`{nfd_string}`"
                            )

                        # ============================================
                        # RESPONSE DISTRIBUTION
                        # ============================================

                        st.markdown(
                            "#### Response Data Distribution Chart"
                        )

                        breakdown = get_value(
                            item,
                            "option_breakdown",
                            []
                        )

                        if breakdown is None:
                            breakdown = []

                        # --------------------------------------------
                        # Distribution bar
                        # --------------------------------------------

                        bar_html = '<div class="dist-container">'

                        for opt in breakdown:

                            pct = get_value(
                                opt,
                                "percentage",
                                0.0
                            )

                            opt_label = get_value(
                                opt,
                                "option",
                                ""
                            )

                            try:
                                pct = float(pct)
                            except (TypeError, ValueError):
                                pct = 0.0

                            if pct > 0:

                                is_correct = bool(
                                    get_value(
                                        opt,
                                        "is_correct",
                                        False
                                    )
                                )

                                is_functional = bool(
                                    get_value(
                                        opt,
                                        "is_functional",
                                        False
                                    )
                                )

                                if is_correct:
                                    color = "#2F8F5B"
                                elif is_functional:
                                    color = "#2C5F8A"
                                else:
                                    color = "#B23A32"

                                display_label = (
                                    str(opt_label)
                                    if pct >= 5
                                    else ""
                                )

                                bar_html += (
                                    '<div '
                                    'class="dist-segment" '
                                    f'style="flex: {pct} 0 auto; '
                                    f'background-color: {color};" '
                                    f'title="{opt_label}: '
                                    f'{pct:.1f}%">'
                                    f'{display_label}'
                                    '</div>'
                                )

                        # --------------------------------------------
                        # Omitted responses
                        # --------------------------------------------

                        omitted_count = get_value(
                            item,
                            "omitted_count",
                            0
                        )

                        try:
                            omitted_count = int(
                                omitted_count
                            )
                        except (TypeError, ValueError):
                            omitted_count = 0

                        if omitted_count > 0:

                            omit_pct = get_value(
                                item,
                                "omitted_percentage",
                                0.0
                            )

                            try:
                                omit_pct = float(
                                    omit_pct
                                )
                            except (TypeError, ValueError):
                                omit_pct = 0.0

                            bar_html += (
                                '<div '
                                'class="dist-segment" '
                                'style="'
                                f'flex: {omit_pct} 0 auto; '
                                'background-color: #92A0BD;'
                                f'" title="Omitted: '
                                f'{omit_pct:.1f}%">'
                                '—'
                                '</div>'
                            )

                        bar_html += '</div>'

                        st.markdown(
                            bar_html,
                            unsafe_allow_html=True
                        )

                        # ============================================
                        # OPTION BREAKDOWN TABLE
                        # ============================================

                        grid_data = []

                        for opt in breakdown:

                            is_correct = bool(
                                get_value(
                                    opt,
                                    "is_correct",
                                    False
                                )
                            )

                            is_functional = bool(
                                get_value(
                                    opt,
                                    "is_functional",
                                    False
                                )
                            )

                            if is_correct:
                                role = "✅ Correct Answer"
                            elif is_functional:
                                role = "Distractor OK"
                            else:
                                role = "❌ Non-functional"

                            percentage = get_value(
                                opt,
                                "percentage",
                                0.0
                            )

                            try:
                                percentage = float(
                                    percentage
                                )
                            except (TypeError, ValueError):
                                percentage = 0.0

                            grid_data.append({
                                "Option Alternative":
                                    get_value(
                                        opt,
                                        "option",
                                        ""
                                    ),

                                "Selection Count":
                                    get_value(
                                        opt,
                                        "count",
                                        0
                                    ),

                                "Distribution Share":
                                    f"{percentage:.1f}%",

                                "Diagnostic Status Evaluation":
                                    role
                            })

                        if grid_data:
                            st.table(grid_data)
                        else:
                            st.info(
                                "No option breakdown data "
                                "was returned for this item."
                            )

            # ========================================================
            # ERROR HANDLING
            # ========================================================

            except Exception as e:

                st.error(
                    f"❌ Computational Execution Failure: {e}"
                )

                with st.expander(
                    "🔍 Technical Error Details",
                    expanded=True
                ):
                    st.exception(e)

else:

    st.info(
        "💡 Please ensure both your Answer Key and Student "
        "Responses Excel templates are uploaded above to "
        "unlock the analysis dashboard."
    )
