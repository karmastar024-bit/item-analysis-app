"""Validate uploaded tables BEFORE analysis. Returns a ValidationResult;
the UI shows errors/warnings and only runs analysis when ok."""
from dataclasses import dataclass, field
import numpy as np
import pandas as pd
from analysis.scoring import TF_MAP, split_accepted

ID_COL_NAMES = {"studentid", "student_id", "id", "student id", "student"}
KEY_LABEL, MAX_LABEL = "KEY", "MAX"


@dataclass
class ValidationResult:
    errors: list = field(default_factory=list)
    warnings: list = field(default_factory=list)
    ids: pd.Series = None
    responses: pd.DataFrame = None   # students x items (raw)
    key: dict = None                 # item -> key cell (str)
    max_scores: dict = None
    info: dict = field(default_factory=dict)

    @property
    def ok(self):
        return not self.errors


def _split_rows(df, special_label):
    idc = df.columns[0]
    is_special = df[idc].astype(str).str.strip().str.upper() == special_label
    return df[~is_special].copy(), (df[is_special].iloc[0] if is_special.any() else None)


def validate(df: pd.DataFrame, kind: str) -> ValidationResult:
    """kind: 'tf' | 'fill' | 'matching' | 'written'"""
    v = ValidationResult()
    if df is None or df.empty:
        v.errors.append("The file has no data."); return v
    if df.shape[1] < 2:
        v.errors.append("At least two columns are needed: StudentID and one item column "
                        "(see the Data Format Guide)."); return v
    if df.columns[0].strip().lower().replace(" ", "") not in {c.replace(" ", "") for c in ID_COL_NAMES}:
        v.errors.append(f"The first column must be 'StudentID' (found '{df.columns[0]}').")
        return v
    dup_cols = [c for c in df.columns if list(df.columns).count(c) > 1]
    if dup_cols:
        v.errors.append(f"Duplicate item column names: {sorted(set(dup_cols))}."); return v

    special = MAX_LABEL if kind == "written" else KEY_LABEL
    body, special_row = _split_rows(df, special)
    idc = df.columns[0]; items = list(df.columns[1:])

    if special_row is None:
        what = ("a row with StudentID = MAX giving each item's maximum score"
                if kind == "written" else
                "an answer-key row with StudentID = KEY")
        v.errors.append(f"Missing {what}.")
    ids = body[idc]
    if ids.isna().any():
        v.errors.append(f"{int(ids.isna().sum())} student row(s) have no StudentID.")
    dups = ids[ids.duplicated(keep=False) & ids.notna()].unique()
    if len(dups):
        v.errors.append("Duplicate StudentID values: " + ", ".join(map(str, dups[:8]))
                        + (" …" if len(dups) > 8 else ""))
    n = len(body)
    if n < 2:
        v.errors.append("At least 2 students are required to calculate discrimination.")
    elif n < 10:
        v.warnings.append(f"Only {n} students: results are very unstable. Use ≥ 30 students if possible.")
    elif n < 30:
        v.warnings.append(f"{n} students: below the recommended minimum of 30 for stable item statistics.")
    resp = body[items]
    miss = int(resp.isna().sum().sum())
    if miss:
        pct = miss / resp.size * 100
        v.warnings.append(f"{miss} empty cell(s) ({pct:.1f}%). " +
                          ("Missing scores are counted as 0 for totals and reported per item."
                           if kind == "written" else "Blank responses are scored as incorrect."))
    empty_items = [c for c in items if resp[c].isna().all()]
    if empty_items:
        v.warnings.append(f"Item(s) with no responses at all: {empty_items}.")

    if special_row is not None:
        key = special_row[items]
        if kind != "written":
            missing_key = [c for c in items if pd.isna(key[c]) or str(key[c]).strip() == ""]
            if missing_key:
                v.errors.append(f"No answer key given for: {missing_key}.")
            v.key = {c: ("" if pd.isna(key[c]) else str(key[c]).strip()) for c in items}
        else:
            mx = {}
            for c in items:
                try:
                    m = float(key[c])
                    if not np.isfinite(m) or m <= 0: raise ValueError
                    mx[c] = m
                except (TypeError, ValueError):
                    v.errors.append(f"Item '{c}': the MAX score must be a number greater than 0.")
            v.max_scores = mx

    if kind == "tf" and v.key:
        bad_key = [c for c, k in v.key.items() if k and k.lower() not in TF_MAP]
        if bad_key: v.errors.append(f"Answer key for {bad_key} must be True/False (or T/F).")
        invalid = sum(1 for c in items for x in resp[c].dropna()
                      if str(x).strip().lower() not in TF_MAP)
        if invalid:
            v.warnings.append(f"{invalid} response(s) are not True/False/T/F; "
                              "they are scored as incorrect.")
    if kind == "fill" and v.key:
        for c, k in v.key.items():
            if k and not split_accepted(k):
                v.errors.append(f"Item '{c}': accepted answer list is empty.")

    if kind == "written":
        num = resp.apply(pd.to_numeric, errors="coerce")
        nonnum = int((num.isna() & resp.notna()).sum().sum())
        if nonnum:
            v.errors.append(f"{nonnum} score(s) are not numbers (use digits, e.g. 7.5).")
        else:
            if (num < 0).any().any():
                v.errors.append("Negative scores found. Scores must be 0 or greater.")
            if v.max_scores:
                over = [c for c in items if c in v.max_scores and (num[c] > v.max_scores[c]).any()]
                if over: v.errors.append(f"Scores above the maximum for: {over}.")
            responses = num
        if v.ok:
            v.responses = num
    elif v.ok:
        v.responses = resp.reset_index(drop=True)
    v.ids = ids.reset_index(drop=True)
    v.info = {"students": n, "items": len(items), "missing_cells": miss}
    return v
