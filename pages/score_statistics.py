"""Test Distribution: descriptive statistics, plots, t-tests, z-tests."""
import numpy as np
import pandas as pd
import streamlit as st
from analysis import statistical_tests as T
from components import charts, explanations as ex
from utils.file_handlers import read_upload, df_to_csv_bytes
from utils.translations import t

TESTS = ["One-sample t-test", "Independent-samples t-test", "Paired-samples t-test",
         "One-sample z-test", "Two-sample z-test"]


def _parse(text):
    vals, bad = [], []
    for tok in text.replace(",", " ").replace(";", " ").split():
        try: vals.append(float(tok))
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
        cols = [c for c in num.columns if num[c].notna().sum() >= 2]
        if not cols: st.error("❌ No numeric column found in the file."); return None
        col = st.selectbox("Column containing the scores", cols, key=f"col_{key}")
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
    st.header("Test distribution & statistical tests")
    st.caption(t("privacy"))
    tab_d, tab_t = st.tabs(["📈 Descriptive statistics & distribution", "🧪 Statistical tests"])

    with tab_d:
        vals = score_input("Total test scores", "desc")
        if vals is None:
            st.info("Provide scores to see the distribution."); 
        else:
            try:
                d = T.descriptive(vals)
                st.dataframe(pd.DataFrame({"Statistic": list(d), "Value": [f"{x:.3f}" if isinstance(x, float) else x
                                                                            for x in d.values()]}),
                             hide_index=True, width="stretch")
                if d["N"] < 10: st.warning("⚠️ Very few scores: shape and spread are unreliable.")
                a, b = st.columns([3, 1.4])
                a.altair_chart(charts.score_hist(vals), width="stretch")
                b.altair_chart(charts.boxplot(vals), width="stretch")
                st.caption("The box shows the middle 50% of scores, the line is the median; dots beyond the "
                           "whiskers are possible outliers.")
            except ValueError as e:
                st.error(f"❌ {e}")

    with tab_t:
        test = st.selectbox("Which test?", TESTS, key="which_test")
        alpha = st.number_input("Significance level α", 0.001, 0.20, 0.05, 0.005, format="%.3f", key="alpha")
        with st.expander("When is this test appropriate?"):
            fam = {"One-sample t-test": "One-sample t-test", "Independent-samples t-test": "Independent-samples t-test (Welch / pooled)"}.get(test, test)
            ltx, txt = ex.TESTS[fam]; st.latex(ltx); st.write(txt)
        if test.endswith("z-test"):
            st.warning("🔔 A z-test is **not** just a 'bigger-sample t-test'. It requires known population "
                       "standard deviation(s). If you only know your own class's SD, choose a t-test.")
        alt = _alt()
        try:
            if test == "One-sample t-test":
                x = score_input("Scores", "t1"); mu = st.number_input("Hypothesised mean (μ₀)", value=50.0)
                if x and st.button("Run test", type="primary"): _show(T.one_sample_t(x, mu, alpha, alt))
            elif test == "Independent-samples t-test":
                st.markdown("**Group 1**"); a = score_input("Group 1 scores", "g1")
                st.markdown("**Group 2**"); b = score_input("Group 2 scores", "g2", allow_session=False)
                eq = st.checkbox("Assume equal variances (pooled)", False,
                                 help="Leave unticked unless you have a reason. Welch's test is safe either way.")
                if a and b and st.button("Run test", type="primary"): _show(T.independent_t(a, b, alpha, alt, eq))
            elif test == "Paired-samples t-test":
                st.markdown("**First measurement (e.g. pre-test)**"); a = score_input("First scores", "p1")
                st.markdown("**Second measurement (e.g. post-test)** – same students, same order")
                b = score_input("Second scores", "p2", allow_session=False)
                if a and b:
                    if len(a) != len(b): st.error(f"❌ Paired scores must have the same length ({len(a)} vs {len(b)}).")
                    elif st.button("Run test", type="primary"): _show(T.paired_t(a, b, alpha, alt))
            elif test == "One-sample z-test":
                x = score_input("Scores", "z1"); c = st.columns(2)
                mu = c[0].number_input("Hypothesised mean (μ₀)", value=50.0)
                sg = c[1].number_input("KNOWN population SD (σ)", min_value=0.0, value=10.0)
                if x and st.button("Run test", type="primary"): _show(T.one_sample_z(x, mu, sg, alpha, alt))
            else:
                a = score_input("Group 1 scores", "zg1"); b = score_input("Group 2 scores", "zg2", allow_session=False)
                c = st.columns(2)
                s1 = c[0].number_input("KNOWN σ for group 1", min_value=0.0, value=10.0)
                s2 = c[1].number_input("KNOWN σ for group 2", min_value=0.0, value=10.0)
                if a and b and st.button("Run test", type="primary"): _show(T.two_sample_z(a, b, s1, s2, alpha, alt))
        except ValueError as e:
            st.error(f"❌ {e}")
        st.info(ex.ASSUMPTIONS)
