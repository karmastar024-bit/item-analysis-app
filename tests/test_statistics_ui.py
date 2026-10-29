import pytest
from scipy import stats
from streamlit.testing.v1 import AppTest

A = "10 12 14 15 18 20 22 19 17"; B = "8 9 12 13 14 15 16 11 10"

def _s():
    from pages import score_statistics; score_statistics.render()

def _go(test, texts=None, nums=None, tab_run=True):
    at = AppTest.from_function(_s, default_timeout=60).run()
    at.selectbox(key="which_test").select(test).run()
    for k, v in (texts or {}).items(): at.text_area(key=k).input(v)
    at = at.run()
    for n in at.number_input:
        if nums and n.label in nums: n.set_value(nums[n.label])
    at = at.run()
    for b in at.button:
        if b.label == "Run test": b.click(); at = at.run(); break
    return at

def metric(at, label): return next(m.value for m in at.metric if m.label == label)

def test_descriptive_tab():
    at = AppTest.from_function(_s, default_timeout=60).run()
    at.text_area(key="txt_desc").input("1 2 2 3 3 4").run()
    at = at.run(); assert not at.exception
    assert any("Mode" in str(df.value) for df in at.dataframe)

def test_one_sample_t():
    at = _go("One-sample t-test", {"txt_t1": A}, {"Hypothesised mean (μ₀)": 12.0})
    assert not at.exception
    ref = stats.ttest_1samp([float(x) for x in A.split()], 12)
    assert metric(at, "Test statistic") == f"{ref.statistic:.3f}"

def test_independent_t_welch():
    at = _go("Independent-samples t-test", {"txt_g1": A, "txt_g2": B})
    ref = stats.ttest_ind([float(x) for x in A.split()], [float(x) for x in B.split()], equal_var=False)
    assert metric(at, "Test statistic") == f"{ref.statistic:.3f}" and not at.exception

def test_paired_t_and_length_mismatch():
    at = _go("Paired-samples t-test", {"txt_p1": B, "txt_p2": A}); assert metric(at, "Degrees of freedom") == "8.00"
    at = _go("Paired-samples t-test", {"txt_p1": B, "txt_p2": "1 2 3"})
    assert "same length" in " ".join(e.value for e in at.error)

def test_one_sample_z_warns_about_sigma():
    at = _go("One-sample z-test", {"txt_z1": A}, {"Hypothesised mean (μ₀)": 12.0, "KNOWN population SD (σ)": 4.0})
    assert not at.exception and metric(at, "Degrees of freedom") == "—"
    assert "known population" in " ".join(w.value for w in at.warning).lower()

def test_two_sample_z():
    at = _go("Two-sample z-test", {"txt_zg1": A, "txt_zg2": B}, {"KNOWN σ for group 1": 4.0, "KNOWN σ for group 2": 5.0})
    assert not at.exception and metric(at, "Significance level α") == "0.05"

def test_non_numeric_input_is_friendly():
    at = _go("One-sample t-test", {"txt_t1": "10 12 abc 14"})
    assert not at.exception and "Not numbers" in " ".join(e.value for e in at.error)

def test_identical_scores_friendly_error():
    at = _go("One-sample t-test", {"txt_t1": "5 5 5 5"}); assert not at.exception
    assert "identical" in " ".join(e.value for e in at.error)

def test_alpha_changes_significance_level_shown():
    at = AppTest.from_function(_s, default_timeout=60).run()
    at.selectbox(key="which_test").select("One-sample t-test").run()
    at.text_area(key="txt_t1").input(A).run()
    at.number_input(key="alpha").set_value(0.10).run()
    [b for b in at.button if b.label == "Run test"][0].click(); at = at.run()
    assert metric(at, "Significance level α") == "0.1"
