"""Read the single-sheet MCQ workbook without writing student data to disk."""
from io import BytesIO
import re

import numpy as np
import pandas as pd

from item_analyzer import ItemAnalyzer
from utils.template_layout import assessment_table


def load_mcq_workbook(raw: bytes):
    if not raw or len(raw) > 10 * 1024 * 1024:
        raise ValueError("Upload a non-empty .xlsx workbook smaller than 10 MB.")
    try:
        frame = pd.read_excel(BytesIO(raw), sheet_name="MCQ", header=None,
                              dtype=str, keep_default_na=False, engine="openpyxl")
    except Exception as exc:
        raise ValueError("Could not read the workbook. Use the .xlsx template and keep the sheet named MCQ.") from exc
    if frame.empty:
        raise ValueError("The MCQ sheet is empty. Download and fill in the template.")
    frame = frame.apply(lambda col: col.str.strip())
    headers = frame.index[frame.iloc[:, 0].str.casefold() == "student id"].tolist()
    if len(headers) != 1:
        raise ValueError("Keep exactly one header row beginning with Student ID.")
    h = headers[0]
    labels = frame.iloc[h].tolist()
    while labels and not labels[-1]:
        labels.pop()
    if labels[:3] != ["Student ID", "Name", "Total Score"]:
        raise ValueError("The first three columns must be Student ID, Name, and Total Score.")
    questions = labels[3:]
    if not questions or any(not re.fullmatch(r"Q[1-9]\d*", q) for q in questions):
        raise ValueError("Use question headers Q1, Q2, Q3, … after Total Score.")
    if len(set(questions)) != len(questions):
        raise ValueError("Question headers must be unique.")
    body = assessment_table(frame)
    is_key = body["Student ID"].str.upper().eq("KEY")
    if is_key.sum() != 1:
        raise ValueError("Include exactly one answer-key row with KEY in the Student ID column.")
    key = body.loc[is_key, questions].iloc[0].str.upper()
    if not key.isin(list("ABCD")).all():
        raise ValueError("Every answer-key cell must contain A, B, C, or D.")
    students = body.loc[~is_key].copy()
    if len(students) < 2:
        raise ValueError("Enter at least two students below the column headers.")
    if students[["Student ID", "Name"]].eq("").any().any():
        raise ValueError("Every student row needs a Student ID and Name.")
    if students["Student ID"].str.casefold().duplicated().any():
        raise ValueError("Student IDs must be unique. Check for duplicate student rows.")
    totals = pd.to_numeric(students["Total Score"], errors="coerce")
    if not np.isfinite(totals).all() or (totals < 0).any():
        raise ValueError("Every student needs a non-negative numeric Total Score (MCQ + all sections).")
    responses = students[questions].apply(lambda col: col.str.upper())
    if not responses.isin(["", "A", "B", "C", "D"]).all().all():
        raise ValueError("Student responses must be A, B, C, D, or blank for an omitted answer.")
    analyzer = ItemAnalyzer()
    analyzer.answer_key = {int(q[1:]): key[q] for q in questions}
    analyzer.answer_key_labels = {int(q[1:]): q for q in questions}
    analyzer.total_questions = len(questions)
    analyzer.total_students = len(students)
    analyzer.student_data = pd.DataFrame({
        "student_id": students["Student ID"].tolist(),
        "name": students["Name"].tolist(),
        "provided_score": totals.tolist(),
        "responses": responses.replace("", None).values.tolist(),
    })
    analyzer.calculate_scores()
    return analyzer


def analyze_mcq_workbook(raw: bytes):
    analyzer = load_mcq_workbook(raw)
    return {"summary": analyzer.get_summary(),
            "items": analyzer.calculate_item_statistics(),
            "students": analyzer.rank_students(), "exam_info": analyzer.exam_info}
