"""Test Distribution: descriptive statistics, plots, t-tests, z-tests."""
from pathlib import Path

import numpy as np
import pandas as pd
import streamlit as st
from analysis import statistical_tests as T
from components import charts, explanations as ex
from utils.file_handlers import read_upload, df_to_csv_bytes
from utils.translations import t

TESTS = ["t-test", "z-test"]

def _parse(text):
    vals, bad = [], []
    for tok in text.replace(",", " ").replace(";", " ").split():
        try:
            value = float(tok)
            if not np.isfinite(value):
                raise ValueError
            vals.append(value)
        except ValueError: bad.append(tok)
    return vals, bad


def score_input(label, key, allow_session=True):
    """Return a list of floats or None. Source: typed / file column / item-analysis totals."""
    srcs = ["Type or paste numbers", "Upload a file column"]
    if allow_session and st.session_state.get("stat_scores"):
        srcs.append(f"Totals from my item analysis ({st.session_state.get('stat_label', '')})")
    src = st.radio(label, srcs, key=f"src_{key}", horizontal=True)
    if src == srcs[0]:
        txt = st.text_area("Scores (separated by spaces, commas or new lines)", key=f"txt_{key}", height=90)
        vals, bad = _parse(txt)
        if bad: st.error(f"❌ Not numbers: {', '.join(bad[:6])}"); return None
        return vals or None
    if src == srcs[1]:
        up = st.file_uploader("Upload .csv or .xlsx", type=["csv", "xlsx"], key=f"up_{key}")
        if up is None: return None
        try: df = read_upload(up)
        except ValueError as e: st.error(f"❌ {e}"); return None
        num = df.apply(pd.to_numeric, errors="coerce")
        cols = [c for c in num.columns if num[c].notna().any()
                and str(c).strip().casefold().replace("_", " ") not in
                {"student id", "studentid", "id", "student name", "name"}]
        preferred = next((c for c in cols if str(c).strip().casefold().replace("_", " ")
                          in {"total scores", "total score", "score", "scores"}), None)
        if preferred is not None:
            cols.remove(preferred)
            cols.insert(0, preferred)
        if not cols: st.error("❌ No numeric column found in the file."); return None
        col = st.selectbox("Column containing the scores", cols, key=f"col_{key}")
        num[col] = num[col].replace([np.inf, -np.inf], np.nan)
        miss = int(num[col].isna().sum())
        if miss: st.warning(f"⚠️ {miss} non-numeric/empty value(s) in this column were ignored.")
        return num[col].dropna().tolist()
    return list(st.session_state["stat_scores"])


def _alt():
    return st.selectbox("Alternative hypothesis", ["two-sided", "greater", "less"], key="alt",
                        format_func={"two-sided": "Two-sided (≠)", "greater": "One-sided (>)",
                                     "less": "One-sided (<)"}.get,
                        help="Choose BEFORE looking at the data. Use two-sided unless you have a "
                             "strong reason for a direction.")


def _show(res):
    st.subheader(res["name"])
    c = st.columns(4)
    c[0].metric("Test statistic", f"{res['statistic']:.3f}")
    c[1].metric("Degrees of freedom", "—" if res["df"] is None else f"{res['df']:.2f}")
    c[2].metric("p-value", f"{res['p_value']:.4f}" if res["p_value"] >= 0.0001 else "< 0.0001")
    c[3].metric("Significance level α", f"{res['alpha']}")
    st.markdown(f"**H₀ (null):** {res['null']}  \n**H₁ (alternative):** {res['alternative']}")
    lo, hi = res["ci"]
    st.markdown(f"**{res['ci_label']}:** [{lo:.3f}, {hi:.3f}]")
    (st.error if res["decision"] == "Reject H0" else st.info)(f"**Decision: {res['decision']}.**  {res['interpretation']}")
    if res["name"].startswith(("One-sided",)) or "alternative" in res and res["alternative"] and "≠" not in res["alternative"]:
        st.caption("One-sided tests give a one-sided p-value; the confidence interval shown is two-sided.")
    for w in res["warnings"]: st.warning("⚠️ " + w)
    with st.expander("Details"):
        st.json({k: (float(v) if isinstance(v, (np.floating, float)) else v) for k, v in res["details"].items()})
    row = {"Test": res["name"], "H0": res["null"], "H1": res["alternative"], "Statistic": res["statistic"],
           "df": res["df"], "p-value": res["p_value"], "alpha": res["alpha"],
           "CI low": lo, "CI high": hi, "Decision": res["decision"]}
    st.download_button("⬇️ Download test result (CSV)", df_to_csv_bytes(pd.DataFrame([row])),
                       "test_result.csv", "text/csv")


def render():
    st.header("Test Distribution")
    st.caption("Explore total scores and compare your class mean with a reference value.")
    template = Path(__file__).resolve().parent.parent / "templates" / "score_statistics_template.xlsx"
    left, right = st.columns([3, 1.4])
    left.caption("File layout: Student ID, Student Name, Total Scores. "
                 "Student Name is optional and is not used in the analysis. "
                 "Replace the example rows with your class scores.")
    if template.exists():
        right.download_button("⬇️ Excel template", template.read_bytes(), template.name,
                              "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                              width="stretch")
    vals = score_input("Total test scores", "desc")
    if vals is None:
        st.info("Upload a file or enter scores to see the distribution and descriptive statistics.")
        return
    try:
        d = T.descriptive(vals)
    except ValueError as e:
        st.error(f"❌ {e}")
        return
    st.subheader("Descriptive statistics")
    for col, (label, key) in zip(st.columns(4), [
        ("Students", "N"), ("Mean", "Mean"), ("Median", "Median"),
        ("Standard deviation", "Std. deviation (sample)")]):
        value = d[key]
        col.metric(label, str(value) if key == "N" else
                   (f"{value:.2f}" if np.isfinite(value) else "—"))
    if d["N"] < 10:
        st.caption("With fewer than 10 scores, interpret the distribution shape cautiously.")
    a, b = st.columns([3, 1.4])
    a.altair_chart(charts.score_hist(vals), width="stretch")
    b.altair_chart(charts.boxplot(vals), width="stretch")
    st.caption("The box contains the middle 50% of scores; its line marks the median. "
               "Dots beyond the whiskers are possible outliers.")
    summary = pd.DataFrame({"Statistic": list(d), "Value": [
        (f"{v:.3f}" if np.isfinite(v) else "—") if isinstance(v, float) else str(v)
        for v in d.values()]})
    with st.expander("All descriptive statistics"):
        st.dataframe(summary, hide_index=True, width="stretch")
        st.download_button("⬇️ Download statistics (CSV)", df_to_csv_bytes(summary),
                           "descriptive_statistics.csv", "text/csv")

    st.subheader("Compare with a reference mean")
    test = st.radio("Choose a test", TESTS, key="which_test", horizontal=True)
    st.caption("One-sample test: compare the mean of the scores above with a hypothesised mean.")
    c = st.columns(2)
    mu = c[0].number_input("Hypothesised mean (μ₀)", value=50.0, key="reference_mean")
    alpha = c[1].number_input("Significance level α", 0.001, 0.20, 0.05, 0.005,
                              format="%.3f", key="alpha")
    sigma = None
    if test == "z-test":
        st.warning("A z-test requires a known population standard deviation. "
                   "If you only know your class's SD, choose a t-test.")
        sigma = st.number_input("KNOWN population SD (σ)", min_value=0.0,
                                value=10.0, key="population_sd")
    alt = _alt()
    with st.expander("When is this test appropriate?"):
        ltx, txt = ex.TESTS[f"One-sample {test}"]
        st.latex(ltx)
        st.write(txt)
        st.write(ex.ASSUMPTIONS)
    if st.button("Run test", type="primary"):
        try:
            result = (T.one_sample_t(vals, mu, alpha, alt) if test == "t-test" else
                      T.one_sample_z(vals, mu, sigma, alpha, alt))
            _show(result)
        except ValueError as e:
            st.error(f"❌ {e}")
