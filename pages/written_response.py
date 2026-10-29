import hashlib
from pathlib import Path
import pandas as pd
import streamlit as st
from analysis.written_analysis import analyze_written
from analysis.binary_analysis import analysis_notes
from components import charts, explanations as ex
from pages.binary_common import show_results
from utils.data_validation import validate
from utils.file_handlers import read_upload, build_pdf_report
from utils.translations import t

SAMPLE = Path(__file__).resolve().parent.parent / "data" / "sample_written.csv"
PC, DC = "Difficulty (p = mean/max)", "Discrimination (D)"


def render():
    st.header("Written / Short Answer / Long Answer / Essay — item analysis")
    st.caption("Written constructed-response items (partial credit)")
    with st.expander("How is this analysed? (not the same as MCQ)", expanded=True):
        st.markdown(
            "Written items can earn many different scores, so they are **not** reduced to right/wrong.\n\n"
            "- **Difficulty** = mean item score ÷ maximum item score (a *normalized difficulty*, "
            "i.e. proportion of the maximum score).\n"
            "- **Discrimination** = (mean score of upper 27% − mean score of lower 27%) ÷ maximum score.\n"
            "- Also shown: corrected item-total correlation (supplementary).\n"
            "- The same decision rules apply, **without** distractor efficiency (not applicable).\n"
            "- Different items may have different maximum scores (e.g. 5, 10, 15).")
    c1, c2 = st.columns([3, 1.4])
    c1.caption("File layout: `StudentID`, one column per item holding the score awarded, and a row with "
               "StudentID = **MAX** giving each item's maximum score.")
    if SAMPLE.exists():
        c2.download_button("⬇️ Sample file", SAMPLE.read_bytes(), SAMPLE.name, width="stretch")
    st.caption(t("privacy"))
    up = st.file_uploader("Upload .csv or .xlsx", type=["csv", "xlsx"], key="up_written")
    if up is None:
        st.info("Upload a file to begin."); return
    try:
        df = read_upload(up)
    except ValueError as e:
        st.error(f"❌ {e}"); return
    v = validate(df, "written")
    for w in v.warnings: st.warning("⚠️ " + w)
    if not v.ok:
        for e in v.errors: st.error("❌ " + e)
        return
    st.success(f"✅ File OK: {v.info['students']} students, {v.info['items']} items.")
    sig = hashlib.md5(up.getvalue()).hexdigest()
    if st.session_state.get("res_written", {}).get("sig") != sig:
        st.session_state.pop("res_written", None)

    st.subheader("Maximum scores and rubric (optional)")
    mdf = pd.DataFrame({"Item": list(v.max_scores), "Max score": list(v.max_scores.values()), "Rubric note": ""})
    ed = st.data_editor(mdf, hide_index=True, disabled=["Item"], width="stretch", key=f"mx_{sig}",
                        column_config={"Max score": st.column_config.NumberColumn(min_value=0.5, step=0.5),
                                       "Rubric note": st.column_config.TextColumn(width="large")})
    name = st.text_input("Assessment name (optional)", key="name_written")
    if st.button("▶ Run analysis", type="primary", key="run_written"):
        mx = dict(zip(ed["Item"], ed["Max score"]))
        if any(not m or m <= 0 for m in mx.values()):
            st.error("❌ Every maximum score must be greater than 0."); return
        over = [c for c in v.responses.columns if (v.responses[c] > mx[c]).any()]
        if over:
            st.error(f"❌ Some scores exceed the maximum for: {over}. Correct the data or raise the maximum."); return
        try:
            out = analyze_written(v.responses, mx)
            totals = v.responses.fillna(0).sum(axis=1)
            rub = {r["Item"]: r["Rubric note"] for _, r in ed.iterrows() if str(r["Rubric note"]).strip()}
            meta = {"Assessment": name or "(not named)", "Item type": "Written / Essay",
                    "Students": v.info["students"], "Items": v.info["items"],
                    "Total maximum": sum(mx.values())}
            notes = analysis_notes(len(totals)) + [
                "Distractor efficiency is not applicable to written items.",
                "Difficulty is normalized (mean ÷ maximum). It is not a proportion of students correct."]
            notes += [f"Rubric – {k}: {x}" for k, x in rub.items()]
            method = [ex.METHOD["Constructed-response analysis (partial credit)"], ex.RULES["Written / Essay"]]
            pdf = build_pdf_report("Item Analysis – Written / Essay", meta,
                                   out[["Item", "Max Score", "Mean Score", PC, DC, "Decision", "Reason"]],
                                   notes, method, charts.pdf_pngs(out, PC, DC))
            st.session_state["res_written"] = dict(sig=sig, df=out, totals=totals.tolist(), meta=meta,
                                                   notes=notes, pdf=pdf, n_items=len(mx),
                                                   scores=v.responses, mx=mx)
        except Exception:
            st.error("❌ The analysis could not be completed. Check your file against the Data Format Guide."); return
    r = st.session_state.get("res_written")
    if r:
        show_results(r, "written_item_analysis", PC, DC, "written", r["meta"]["Total maximum"])
        st.subheader("Score distribution for one item")
        item = st.selectbox("Item", list(r["mx"]), key="wr_item")
        st.altair_chart(charts.item_score_bars(r["scores"][item], r["mx"][item]), width="stretch")
