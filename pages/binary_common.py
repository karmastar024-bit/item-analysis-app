"""Shared workflow for binary-scored item types (T/F, Fill, Matching) and
the shared results display (also used by the written-response page)."""
import hashlib
import pandas as pd
import streamlit as st
from analysis.binary_analysis import analyze_binary, analysis_notes
from analysis import scoring
from components import charts, tables, explanations as ex
from components.navigation import go
from utils.data_validation import validate
from utils.file_handlers import read_upload, build_pdf_report
from utils.translations import t

CFG = {
 "tf": dict(title="True or False", sample="sample_true_false.csv", col="Correct answer",
            help="Enter True or False (T/F also accepted).",
            doc=("Each statement is scored **1** if the response matches the key (True/T or False/F, "
                 "case-insensitive), otherwise **0**. Blank or invalid responses are scored 0."),
            de="Distractor efficiency is **not applicable** to True/False: there are only two options "
               "and no set of wrong options to evaluate."),
 "fill": dict(title="Fill in the Blanks", sample="sample_fill_blank.csv", col="Accepted answers (separate with |)",
              help="Put every acceptable answer in the cell, separated by |  e.g. Paro | Paro Dzong",
              doc=("A response is correct (**1**) if, after normalization, it equals **any** accepted answer; "
                   "otherwise **0**. Normalization: case ignored (optional), extra spaces removed, punctuation "
                   "removed (optional)."),
              de="Distractor efficiency is **not applicable**: students write their own answers."),
 "matching": dict(title="Matching", sample="sample_matching.csv", col="Correct match",
                  help="The letter or number the student should choose for this prompt.",
                  doc=("**Each prompt is one item worth 1 point.** A response is correct only if it equals the "
                       "key (case-insensitive). Blank = incorrect. There is no partial credit within a prompt."),
                  de="Distractor efficiency is **not applicable** to matching items."),
}


def _sig(up):
    return hashlib.md5(up.getvalue()).hexdigest()


def render(kind):
    cfg = CFG[kind]; res_key = f"res_{kind}"
    st.header(f"{cfg['title']} — item analysis")
    st.caption("Selected-response item" if kind != "fill" else "Short constructed-response item")
    with st.expander("How is this item type scored?"):
        st.markdown(cfg["doc"]); st.markdown(cfg["de"])
    sample = __import__("pathlib").Path(__file__).resolve().parent.parent / "data" / cfg["sample"]
    c1, c2 = st.columns([3, 1.4])
    c1.caption("File layout: `StudentID`, item columns … and a row with StudentID = **KEY**. See Data Format Guide.")
    if sample.exists():
        c2.download_button("⬇️ Sample file", sample.read_bytes(), sample.name, width="stretch")
    st.caption(t("privacy"))

    up = st.file_uploader("Upload .csv or .xlsx", type=["csv", "xlsx"], key=f"up_{kind}")
    if up is None:
        st.info("Upload a file to begin."); return
    try:
        df = read_upload(up)
    except ValueError as e:
        st.error(f"❌ {e}"); return
    v = validate(df, kind)
    for w in v.warnings: st.warning("⚠️ " + w)
    if not v.ok:
        for e in v.errors: st.error("❌ " + e)
        st.caption("Fix the problems above and upload the file again."); return
    st.success(f"✅ File OK: {v.info['students']} students, {v.info['items']} items.")

    sig = _sig(up)
    if st.session_state.get(res_key, {}).get("sig") != sig:
        st.session_state.pop(res_key, None)

    st.subheader("Answer key")
    kdf = pd.DataFrame({"Item": list(v.key), cfg["col"]: list(v.key.values())})
    edited = st.data_editor(kdf, hide_index=True, disabled=["Item"], width="stretch",
                            key=f"key_{kind}_{sig}", column_config={cfg["col"]: st.column_config.TextColumn(
                                cfg["col"], help=cfg["help"], width="large")})
    key = dict(zip(edited["Item"], edited[cfg["col"]].fillna("").astype(str)))
    opts = {}
    if kind == "fill":
        o1, o2 = st.columns(2)
        opts["ignore_case"] = o1.checkbox("Ignore upper/lower case", True)
        opts["strip_punct"] = o2.checkbox("Ignore punctuation", False)
    elif kind == "matching":
        opts["ignore_case"] = st.checkbox("Ignore upper/lower case", True)
    name = st.text_input("Assessment name (optional)", key=f"name_{kind}")

    if st.button("▶ Run analysis", type="primary", key=f"run_{kind}"):
        if any(not k.strip() for k in key.values()):
            st.error("❌ Every item needs an answer in the key."); return
        try:
            with st.spinner("Analysing…"):
                resp = v.responses
                if kind == "tf": sc = scoring.score_true_false(resp, key)
                elif kind == "fill":
                    sc = scoring.score_fill_blank(resp, {c: scoring.split_accepted(k) for c, k in key.items()}, **opts)
                else: sc = scoring.score_matching(resp, key, **opts)
                out = analyze_binary(sc)
                totals = sc.sum(axis=1)
                meta = {"Assessment": name or "(not named)", "Item type": cfg["title"],
                        "Students": v.info["students"], "Items": v.info["items"]}
                notes = analysis_notes(len(sc)) + [cfg["de"].replace("**", "")]
                method = [ex.METHOD["Fill-in-the-Blank scoring"] if kind == "fill" else
                          ex.METHOD["Matching scoring"] if kind == "matching" else
                          "True/False responses scored 0/1 against the key.",
                          ex.METHOD["Selected-response analysis (binary items)"], ex.RULES["True or False"]]
                pdf = build_pdf_report(f"Item Analysis – {cfg['title']}", meta,
                                       out[["Item", "Difficulty (p)", "Discrimination (D)", "Decision", "Reason"]],
                                       notes, method, charts.pdf_pngs(out, "Difficulty (p)", "Discrimination (D)"))
            st.session_state[res_key] = dict(sig=sig, df=out, totals=totals.tolist(), meta=meta,
                                             notes=notes, pdf=pdf, n_items=sc.shape[1])
        except Exception:
            st.error("❌ The analysis could not be completed. Please check your file and answer key "
                     "against the Data Format Guide."); return
    r = st.session_state.get(res_key)
    if r: show_results(r, f"{kind}_item_analysis", "Difficulty (p)", "Discrimination (D)", kind,
                       max_total=r["n_items"])


def show_results(r, base, pcol, dcol, key, max_total):
    df = r["df"]
    st.divider(); st.subheader("Results")
    tables.decision_metrics(df)
    tab1, tab2, tab3, tab4 = st.tabs(["📋 Table", "📊 Charts", "💬 Why each decision", "⬇️ Download"])
    with tab1:
        tables.results_table(df)
    with tab2:
        a, b = st.columns(2)
        a.altair_chart(charts.difficulty_hist(df, pcol), width="stretch")
        b.altair_chart(charts.discrimination_hist(df, dcol), width="stretch")
        c, d = st.columns(2)
        c.altair_chart(charts.decision_bar(df), width="stretch")
        d.altair_chart(charts.item_scatter(df, pcol, dcol), width="stretch")
        st.altair_chart(charts.score_hist(r["totals"]), width="stretch")
    with tab3:
        tables.item_cards(df)
    with tab4:
        meta = pd.DataFrame(list(r["meta"].items()), columns=["Field", "Value"])
        notes = pd.DataFrame({"Notes": r["notes"]})
        tables.downloads(df, base, {"Assessment": meta, "Notes": notes}, r["pdf"], key=key)
        st.caption("Downloads contain item-level results only; no student IDs or names are included.")
    for n in r["notes"]: st.caption("• " + n)
    if st.button("Use these total scores in Test Distribution", key=f"toS_{key}"):
        st.session_state["stat_scores"] = r["totals"]; st.session_state["stat_label"] = r["meta"]["Item type"]
        go("statistics")
