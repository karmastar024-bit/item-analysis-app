"""Exercise the actual downloaded template and the single-upload workflow."""
from io import BytesIO
from pathlib import Path
from zipfile import ZipFile
import xml.etree.ElementTree as ET

import pytest
from utils.mcq_workbook import load_mcq_workbook, analyze_mcq_workbook

ROOT = Path(__file__).resolve().parent.parent
NS = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"


def completed_template(changes=None, template="mcq", key_value="A", response_value=None):
    """Fill input cells in the real template, keeping its structure/styles."""
    cells = {f"{col}8": key_value for col in "DEFGHIJKLM"}
    for row, score in [(10, 90), (11, 60), (12, 30), (13, 10)]:
        cells.update({f"A{row}": f"00{row}", f"B{row}": f"Student {row}", f"C{row}": score})
        cells.update({f"{col}{row}": response_value if response_value is not None else
                      ("B" if row < 12 else "A") for col in "DEFGHIJKLM"})
    cells.update(changes or {})
    output = BytesIO()
    with ZipFile(ROOT / f"templates/{template}_template.xlsx") as source, ZipFile(output, "w") as dest:
        for info in source.infolist():
            data = source.read(info.filename)
            if info.filename == "xl/worksheets/sheet1.xml":
                tree = ET.fromstring(data)
                sheet_data = tree.find(f"{NS}sheetData")
                for address, value in cells.items():
                    row_num = ''.join(c for c in address if c.isdigit())
                    row = sheet_data.find(f"{NS}row[@r='{row_num}']")
                    if row is None:
                        row = ET.SubElement(sheet_data, f"{NS}row", r=row_num)
                    cell = row.find(f"{NS}c[@r='{address}']")
                    if cell is None:
                        cell = ET.SubElement(row, f"{NS}c", r=address)
                    for child in list(cell): cell.remove(child)
                    cell.set("t", "inlineStr")
                    ET.SubElement(ET.SubElement(cell, f"{NS}is"), f"{NS}t").text = str(value)
                data = ET.tostring(tree)
            dest.writestr(info, data)
    return output.getvalue()


@pytest.mark.parametrize("template,kind,key,response", [
    ("true_false", "tf", "True", "True"),
    ("fill_blank", "fill", "Paro|Paro Dzong", "Paro"),
    ("matching", "matching", "C", "C"),
    ("written", "written", 5, 3),
])
def test_shared_templates_upload_and_analyze(template, kind, key, response):
    from utils.file_handlers import read_upload
    from utils.data_validation import validate
    from analysis import scoring
    from analysis.binary_analysis import analyze_binary
    from analysis.written_analysis import analyze_written
    raw = completed_template({"B10": "", "C10": ""}, template, key, response)
    class Upload:
        name = template + ".xlsx"
        def getvalue(self): return raw
    table = read_upload(Upload())
    result = validate(table, kind)
    assert result.ok, result.errors
    assert result.info["students"] == 4
    assert list(result.responses) == [f"Q{i}" for i in range(1, 11)]
    assert result.ids.iloc[0] == "0010"
    if kind == "written":
        out = analyze_written(result.responses, result.max_scores)
        assert out["Mean Score"].eq(3).all()
    else:
        if kind == "fill":
            scores = scoring.score_fill_blank(result.responses, {q: scoring.split_accepted(k) for q, k in result.key.items()})
        elif kind == "tf":
            scores = scoring.score_true_false(result.responses, result.key)
        else:
            scores = scoring.score_matching(result.responses, result.key)
        assert scores.eq(1).all().all()
        out = analyze_binary(scores)
    assert len(out) == 10


def test_legacy_mcq_key_below_header():
    """Older MCQ downloads still work after the layout change."""
    import pandas as pd
    from utils.template_layout import assessment_table
    frame = pd.DataFrame([
        ["Student ID", "Name", "Total Score", "Q1"],
        ["KEY", "Answer key", "", "A"],
        ["001", "Student", "5", "A"],
    ])
    table = assessment_table(frame)
    assert table["Student ID"].tolist() == ["KEY", "001"]
    assert table["Q1"].tolist() == ["A", "A"]


def test_template_scores_and_overall_grouping():
    raw = completed_template({"D10": ""})
    a = load_mcq_workbook(raw)
    assert a.total_students == 4 and a.total_questions == 10
    assert a.student_data.student_id.iloc[0] == "0010"
    assert a.student_data.provided_score.tolist() == [90, 60, 30, 10]
    assert a.scores.tolist() == [0, 0, 10, 10]
    # Highest overall student has the lowest MCQ score: use overall grouping.
    results = analyze_mcq_workbook(raw)
    assert results["items"][0].discrimination == -1
    assert results["items"][0].difficulty == .5


@pytest.mark.parametrize("changes, message", [
    ({"A11": "0010"}, "unique"),
    ({"B10": ""}, "Name"),
    ({"C10": ""}, "Total Score"),
    ({"C10": "inf"}, "Total Score"),
    ({"C10": -1}, "Total Score"),
    ({"D8": ""}, "answer-key"),
    ({"D10": "E"}, "responses"),
    ({"A10": "KEY"}, "exactly one"),
    ({"E9": "Q1"}, "unique"),
    ({"A8": ""}, "exactly one"),
])
def test_bad_workbooks_are_rejected(changes, message):
    with pytest.raises(ValueError, match=message):
        load_mcq_workbook(completed_template(changes))


def _upload_page(raw):
    import streamlit as st
    from components.mcq_upload import render_upload
    from dataclasses import asdict, is_dataclass
    from enum import Enum
    def sanitize(v):
        if is_dataclass(v): return sanitize(asdict(v))
        if isinstance(v, Enum): return v.value
        if isinstance(v, dict): return {k:sanitize(x) for k,x in v.items()}
        if isinstance(v, list): return [sanitize(x) for x in v]
        return v
    class Upload:
        name = "assessment.xlsx"
        def getvalue(self): return st.session_state.get("test_raw", raw)
    st.file_uploader = lambda *args, **kwargs: Upload()
    render_upload(sanitize)


def test_single_upload_and_stale_results():
    from streamlit.testing.v1 import AppTest
    at = AppTest.from_function(_upload_page, args=(completed_template(),)).run()
    next(b for b in at.button if b.label == "▶ Run analysis").click().run()
    assert not at.exception
    assert at.session_state["analysis_results"]["summary"]["total_students"] == 4
    at.session_state["test_raw"] = completed_template({"C10": 80})
    at.run()
    assert "analysis_results" not in at.session_state
