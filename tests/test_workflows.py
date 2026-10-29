"""End-to-end UI tests: a fake uploader feeds bytes to each page."""
import io
from pathlib import Path
import pandas as pd, pytest
from streamlit.testing.v1 import AppTest

DATA = Path(__file__).resolve().parent.parent / "data"

def _script(page, filename, raw):
    import streamlit as st
    class F:
        name = filename
        def getvalue(self): return raw
    st.file_uploader = lambda *a, **k: F()
    import importlib
    importlib.import_module(f"pages.{page}").render()

def run(page, filename, raw, click=True):
    at = AppTest.from_function(_script, args=(page, filename, raw), default_timeout=90).run()
    if click and not at.exception and at.button:
        for b in at.button:
            if b.label.startswith("▶"): b.click(); at = at.run(); break
    return at

def sample(name): return (DATA / name).read_bytes()
def csv(df): return df.to_csv(index=False).encode()
def msgs(at, kind): return " ".join(getattr(at, kind)[i].value for i in range(len(getattr(at, kind))))

KINDS = [("true_false","sample_true_false.csv"),("fill_blank","sample_fill_blank.csv"),
         ("matching","sample_matching.csv"),("written_response","sample_written.csv")]

@pytest.mark.parametrize("page,f", KINDS)
def test_sample_runs_and_produces_results(page, f):
    at = run(page, f, sample(f))
    assert not at.exception, at.exception
    key = {"true_false":"res_tf","fill_blank":"res_fill","matching":"res_matching","written_response":"res_written"}[page]
    assert key in at.session_state, "no result stored"
    r = at.session_state[key]["df"]
    assert "Decision" in r and r["Decision"].isin(["RETAIN","REVIEW","REVISE","DISCARD"]).all()
    assert r["Reason"].str.len().min() > 10
    assert "Distractor" not in " ".join(r.columns)       # DE never computed for these types
    assert at.download_button, "downloads missing"

def test_tf_edge_items_behave():
    at = run("true_false","s.csv",sample("sample_true_false.csv"))
    r = at.session_state["res_tf"]["df"].set_index("Item")
    assert r.loc["Q7","Discrimination (D)"] < 0 and r.loc["Q7","Decision"]=="DISCARD"   # negative D
    assert r.loc["Q6","Decision"] in ("REVISE","DISCARD")                              # very hard
    assert r.loc["Q8","Difficulty (p)"] > 0.8                                          # very easy

def test_fill_multiple_answers_and_case():
    at = run("fill_blank","s.csv",sample("sample_fill_blank.csv"))
    r = at.session_state["res_fill"]["df"].set_index("Item")
    raw = pd.read_csv(DATA/"sample_fill_blank.csv", dtype=str)
    body = raw[raw.StudentID!="KEY"]
    exp = body["Q2"].fillna("").str.strip().str.casefold().isin(["paro taktsang","tiger's nest","taktsang"]).sum()
    assert r.loc["Q2","Number Correct"] == exp

def test_matching_missing_counts_incorrect():
    at = run("matching","s.csv",sample("sample_matching.csv"))
    r = at.session_state["res_matching"]["df"]
    assert (r["Number Correct"]+r["Number Incorrect"]==40).all()

def test_written_different_max_scores():
    at = run("written_response","s.csv",sample("sample_written.csv"))
    r = at.session_state["res_written"]["df"].set_index("Item")
    assert list(r["Max Score"])==[5,10,15,20] and r.loc["Q2","Missing Scores"]==1 and r["Missing Scores"].sum()==1
    assert ((r["Difficulty (p = mean/max)"]>=0)&(r["Difficulty (p = mean/max)"]<=1)).all()

# ---------------- graceful failure ----------------
def good(): return pd.read_csv(DATA/"sample_true_false.csv", dtype=str)
CASES = {
 "empty file":            ("x.csv", b"", "empty"),
 "wrong type":            ("x.txt", b"hello", "Unsupported"),
 "garbage bytes xlsx":    ("x.xlsx", b"not a workbook", "could not be read"),
 "headers only":          ("x.csv", b"StudentID,Q1,Q2\n", "no student rows"),
 "no id column":          ("x.csv", csv(good().rename(columns={"StudentID":"Name"})), "StudentID"),
 "one column":            ("x.csv", b"StudentID\nS1\nS2\n", "two columns"),
 "missing key row":       ("x.csv", csv(good()[good().StudentID!="KEY"]), "Missing"),
 "duplicate ids":         ("x.csv", csv(pd.concat([good(), good().iloc[[2]]])), "Duplicate StudentID"),
 "blank key cell":        ("x.csv", csv(good().assign(Q1=lambda d: d.Q1.where(d.StudentID!="KEY"))), "No answer key"),
 "bad key value":         ("x.csv", csv(good().assign(Q1=lambda d: d.Q1.where(d.StudentID!="KEY","maybe"))), "True/False"),
 "single student":        ("x.csv", csv(good().iloc[:2]), "At least 2 students"),
}
@pytest.mark.parametrize("name", list(CASES))
def test_invalid_input_fails_gracefully(name):
    fn, raw, expect = CASES[name]
    at = run("true_false", fn, raw, click=False)
    assert not at.exception, at.exception                          # no traceback
    shown = msgs(at, "error")
    assert expect.lower() in shown.lower(), shown
    assert not any(b.label.startswith("▶") for b in at.button)       # analysis not offered

def test_small_sample_warns_but_runs():
    at = run("true_false","x.csv",csv(good().iloc[:7]))             # KEY + 6 students
    assert not at.exception and "unstable" in msgs(at,"warning")
    assert "res_tf" in at.session_state

def test_missing_and_invalid_responses_warn():
    g = good(); g.loc[3,"Q1"]=None; g.loc[4,"Q2"]="banana"
    at = run("true_false","x.csv",csv(g))
    w = msgs(at,"warning"); assert "empty cell" in w and "not True/False" in w and not at.exception

def test_written_validation():
    w = pd.read_csv(DATA/"sample_written.csv", dtype=str)
    bad = w.copy(); bad.loc[5,"Q1"]="9"                           # exceeds max 5
    assert "above the maximum" in msgs(run("written_response","x.csv",csv(bad),click=False),"error")
    bad = w.copy(); bad.loc[5,"Q1"]="abc"
    assert "not numbers" in msgs(run("written_response","x.csv",csv(bad),click=False),"error")
    bad = w.copy(); bad.loc[5,"Q1"]="-2"
    assert "Negative" in msgs(run("written_response","x.csv",csv(bad),click=False),"error")
    bad = w[w.StudentID!="MAX"]
    assert "MAX" in msgs(run("written_response","x.csv",csv(bad),click=False),"error")
