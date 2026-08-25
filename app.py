import streamlit as st
import tempfile
import math
from pathlib import Path
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
    /* Styling variables */
    html, body, [data-testid="stAppViewContainer"] {
        background-color: #F3F5F8 !important;
        color: #16233E !important;
    }

    h1, h2, h3 {
        font-family: 'Space Grotesk', sans-serif !important;
    }

    /* Custom Container Blocks */
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

    /* Custom Badges */
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

    /* Distribution Bar Components */
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
# HEADER SECTION
# ============================================================

st.markdown("""
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
""", unsafe_allow_html=True)


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
# STATUS CLASS HELPER
# ============================================================

def get_status_class(status, block_type="diff"):

    if status in ["Ideal", "Good"]:
        return "good"

    if status in ["Too Easy", "Poor"]:
        return "mid"

    return "poor"


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

                # ====================================================
                # 1. CREATE TEMPORARY DIRECTORY
                # ====================================================

                with tempfile.TemporaryDirectory() as tmp_dir:

                    tmp_path = Path(tmp_dir)

                    key_path = tmp_path / "key.xlsx"
                    data_path = tmp_path / "data.xlsx"

                    # Write uploaded files to temporary directory
                    key_path.write_bytes(key_file.getvalue())
                    data_path.write_bytes(data_file.getvalue())

                    # ====================================================
                    # 2. RUN ITEM ANALYSIS ENGINE
                    # ====================================================

                    analyzer = ItemAnalyzer()

                    raw_results = analyzer.run_analysis(
                        str(key_path),
                        str(data_path)
                    )


                # ====================================================
                # 3. SANITIZE RESULTS
                # ====================================================

                def sanitize(data):

                    if isinstance(data, dict):
                        return {
                            k: sanitize(v)
                            for k, v in data.items()
                        }

                    if isinstance(data, list):
                        return [
                            sanitize(i)
                            for i in data
                        ]

                    if isinstance(data, float):

                        if math.isnan(data) or math.isinf(data):
                            return 0.0

                    return data


                results = sanitize(raw_results)


                # ====================================================
                # 4. DISPLAY GLOBAL METRICS
                # ====================================================

                summary = results.get("summary", {})

                st.markdown("### 📊 Overall Test Summary")

                metric_col1, metric_col2 = st.columns(2)


                with metric_col1:

                    st.metric(
                        label="Total Students Scaled",
                        value=summary.get(
                            "total_students",
                            0
                        )
                    )


                with metric_col2:

                    st.metric(
                        label="Total Evaluated Items",
                        value=summary.get(
                            "total_questions",
                            0
                        )
                    )


                # ====================================================
                # 5. PER-QUESTION ANALYTICS
                # ====================================================

                st.markdown("### 🔬 Per-Question Analysis")

                st.caption(
                    "Click a question card below to expand its "
                    "full response distribution profile and option breakdowns."
                )


                items = results.get("items", [])


                # ====================================================
                # 6. LOOP THROUGH QUESTIONS
                # ====================================================

                for idx, item in enumerate(items):

                    q_text = item.get(
                        "question",
                        f"Question {idx + 1}"
                    )

                    rec = item.get(
                        "recommendation",
                        "Review"
                    ).lower()


                    # =================================================
                    # QUESTION EXPANDER
                    # =================================================

                    with st.expander(
                        f"📦 {q_text} — Recommendation: {rec.upper()}"
                    ):


                        # =============================================
                        # METRIC GAUGES
                        # =============================================

                        g_col1, g_col2 = st.columns(2)


                        # ---------------------------------------------
                        # DIFFICULTY
                        # ---------------------------------------------

                        with g_col1:

                            diff_val = item.get(
                                "difficulty",
                                0.0
                            )

                            diff_status = item.get(
                                "difficulty_status",
                                "N/A"
                            )


                            st.metric(
                                label="Difficulty Level",
                                value=f"{diff_val:.3f}",
                                delta=diff_status,
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


                        # ---------------------------------------------
                        # DISCRIMINATION
                        # ---------------------------------------------

                        with g_col2:

                            disc_val = item.get(
                                "discrimination",
                                0.0
                            )

                            disc_status = item.get(
                                "discrimination_status",
                                "N/A"
                            )


                            st.metric(
                                label="Discrimination Power",
                                value=f"{disc_val:.3f}",
                                delta=disc_status,
                                delta_color="off"
                            )


                            # Normalize discrimination value
                            # from -1...+1 to 0...1

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


                        # =============================================
                        # EXTRA METRICS
                        # =============================================

                        st.markdown("---")


                        eff_rate = item.get(
                            "distractor_efficiency",
                            0.0
                        )


                        nfds_list = item.get(
                            "non_functional_distractors",
                            []
                        )


                        m_col1, m_col2 = st.columns(2)


                        # ---------------------------------------------
                        # DISTRACTOR EFFICIENCY
                        # ---------------------------------------------

                        with m_col1:

                            st.write(
                                f"**Distractor Efficiency:** "
                                f"`{eff_rate:.0f}%`"
                            )


                        # ---------------------------------------------
                        # NON-FUNCTIONAL DISTRACTORS
                        # ---------------------------------------------

                        with m_col2:

                            nfd_string = (
                                ", ".join(nfds_list)
                                if nfds_list
                                else "None"
                            )


                            st.write(
                                f"**Flagged NFDs:** "
                                f"`{nfd_string}`"
                            )


                        # =============================================
                        # RESPONSE DISTRIBUTION
                        # =============================================

                        st.markdown(
                            "#### Response Data Distribution Chart"
                        )


                        breakdown = item.get(
                            "option_breakdown",
                            []
                        )


                        # =============================================
                        # CONSTRUCT DISTRIBUTION BAR
                        # =============================================

                        bar_html = (
                            '<div class="dist-container">'
                        )


                        for opt in breakdown:

                            pct = opt.get(
                                "percentage",
                                0.0
                            )

                            opt_label = opt.get(
                                "option",
                                ""
                            )


                            if pct > 0:

                                # Correct answer = green
                                # Functional distractor = blue
                                # Non-functional distractor = red

                                if opt.get("is_correct"):

                                    color = "#2F8F5B"

                                elif opt.get("is_functional"):

                                    color = "#2C5F8A"

                                else:

                                    color = "#B23A32"


                                display_label = (
                                    opt_label
                                    if pct >= 5
                                    else ""
                                )


                                bar_html += (
                                    f'<div '
                                    f'class="dist-segment" '
                                    f'style="'
                                    f'flex: {pct} 0 auto; '
                                    f'background-color: {color};'
                                    f'" '
                                    f'title="{opt_label}: '
                                    f'{pct:.1f}%">'
                                    f'{display_label}'
                                    f'</div>'
                                )


                        # =============================================
                        # OMITTED RESPONSES
                        # =============================================

                        omitted_count = item.get(
                            "omitted_count",
                            0
                        )


                        if omitted_count > 0:

                            omit_pct = item.get(
                                "omitted_percentage",
                                0.0
                            )


                            bar_html += (
                                f'<div '
                                f'class="dist-segment" '
                                f'style="'
                                f'flex: {omit_pct} 0 auto; '
                                f'background-color: #92A0BD;'
                                f'" '
                                f'title="Omitted: '
                                f'{omit_pct:.1f}%">'
                                f'—'
                                f'</div>'
                            )


                        bar_html += "</div>"


                        st.markdown(
                            bar_html,
                            unsafe_allow_html=True
                        )


                        # =============================================
                        # OPTION BREAKDOWN TABLE
                        # =============================================

                        grid_data = []


                        for opt in breakdown:

                            if opt.get("is_correct"):

                                role = "✅ Correct Answer"

                            elif opt.get("is_functional"):

                                role = "Distractor OK"

                            else:

                                role = "❌ Non-functional"


                            grid_data.append({

                                "Option Alternative":
                                    opt.get("option"),

                                "Selection Count":
                                    opt.get("count"),

                                "Distribution Share":
                                    f"{opt.get('percentage', 0.0):.1f}%",

                                "Diagnostic Status Evaluation":
                                    role

                            })


                        st.table(grid_data)


            # ========================================================
            # ERROR HANDLING
            # ========================================================

            except Exception as e:

                st.error(
                    f"❌ Computational Execution Failure: {e}"
                )

                # Show detailed traceback during development
                with st.expander(
                    "🔍 Technical Error Details"
                ):

                    st.exception(e)


# ============================================================
# FILE UPLOAD REMINDER
# ============================================================

else:

    st.info(
        "💡 Please ensure both your Answer Key and Student "
        "Responses Excel templates are uploaded above to "
        "unlock the analysis dashboard."
    )
