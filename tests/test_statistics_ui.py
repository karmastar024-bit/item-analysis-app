import pytest
from scipy import stats
from streamlit.testing.v1 import AppTest

A = "10 12 14 15 18 20 22 19 17"; B = "8 9 12 13 14 15 16 11 10"

def _s():
    from pages import score_statistics; score_statistics.render()

def _go(test="t-test", scores=A, nums=None):
    at = AppTest.from_function(_s, default_timeout=60).run()
    at.text_area(key="txt_desc").input(scores).run()
    if not at.radio or not any(r.key == "which_test" for r in at.radio):
        return at
    at.radio(key="which_test").set_value(test).run()
    for n in at.number_input:
        if nums and n.label in nums:
            n.set_value(nums[n.label])
    at.run()
    next(b for b in at.button if b.label == "Run test").click().run()
    return at


def metric(at, label):
    return next(m.value for m in at.metric if m.label == label)


def test_descriptive_and_simple_selector():
    at = _go(scores="1 2 2 3 3 4")
    assert not at.exception
    assert metric(at, "Mean") == "2.50"
    assert metric(at, "Median") == "2.50"
    assert at.radio(key="which_test").options == ["t-test", "z-test"]
    assert any("Mode" in str(df.value) for df in at.dataframe)
    assert len(at.get("vega_lite_chart")) + len(at.get("arrow_vega_lite_chart")) == 2


def test_one_sample_t():
    at = _go(nums={"Hypothesised mean (μ₀)": 12.0})
    assert not at.exception
    ref = stats.ttest_1samp([float(x) for x in A.split()], 12)
    assert metric(at, "Test statistic") == f"{ref.statistic:.3f}"


def test_one_sample_z_warns_about_sigma():
    at = _go("z-test", nums={"Hypothesised mean (μ₀)": 12.0, "KNOWN population SD (σ)": 4.0})
    assert not at.exception and metric(at, "Degrees of freedom") == "—"
    assert "known population" in " ".join(w.value for w in at.warning).lower()
    import numpy as np
    expected = (np.mean([float(x) for x in A.split()]) - 12) / (4 / 3)
    assert metric(at, "Test statistic") == f"{expected:.3f}"


def test_non_numeric_input_is_friendly():
    at = _go(scores="10 12 abc 14")
    assert not at.exception and "Not numbers" in " ".join(e.value for e in at.error)


def test_identical_scores_friendly_error():
    at = _go(scores="5 5 5 5")
    assert not at.exception
    assert "identical" in " ".join(e.value for e in at.error)


def test_alpha_changes_significance_level_shown():
    at = _go(nums={"Significance level α": 0.10})
    assert metric(at, "Significance level α") == "0.1"


def test_template_round_trip_and_score_column(monkeypatch):
    from io import BytesIO
    from pathlib import Path
    from pages import score_statistics as page
    from utils.file_handlers import read_upload
    upload = BytesIO((Path(__file__).resolve().parents[1] / "templates" /
                      "score_statistics_template.xlsx").read_bytes())
    upload.name = "scores.xlsx"
    frame = read_upload(upload)
    assert list(frame.columns) == ["Student ID", "Student Name", "Total Scores"]
    monkeypatch.setattr(page.st, "radio", lambda *a, **k: "Upload a file column")
    monkeypatch.setattr(page.st, "file_uploader", lambda *a, **k: upload)
    def select(label, columns, **kwargs):
        assert columns[0] == "Total Scores"
        assert "Student ID" not in columns
        return columns[0]
    monkeypatch.setattr(page.st, "selectbox", select)
    assert page.score_input("Scores", "test", allow_session=False) == [52,68,74,81,65,90,77,61]
