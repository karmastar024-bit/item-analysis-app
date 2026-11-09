"""Item analysis for binary-scored items (MCQ, T/F, Fill, Matching)."""
import numpy as np
import pandas as pd
from .difficulty import difficulty_binary, difficulty_label
from .discrimination import (discrimination_ul, discrimination_label,
                             upper_lower_indices, group_size)
from .decision import decide, PLAIN


def analyze_binary(scores: pd.DataFrame) -> pd.DataFrame:
    """scores: students x items of 0/1. Returns one row per item."""
    n = len(scores)
    totals = scores.sum(axis=1).to_numpy(dtype=float)
    rows = []
    for c in scores.columns:
        x = scores[c].to_numpy(dtype=float)
        p = difficulty_binary(x)
        d = discrimination_ul(x, totals, 1.0) if n >= 2 else float("nan")
        dec, reason = decide(p, d)
        rows.append({
            "Item": c,
            "Number Correct": int(np.nansum(x)),
            "Number Incorrect": int(n - np.nansum(x)),
            "Difficulty (p)": round(p, 2),
            "Difficulty Level": difficulty_label(p),
            "Discrimination (D)": round(d, 2) if not np.isnan(d) else np.nan,
            "Discrimination Level": discrimination_label(d),
            "Decision": dec,
            "Reason": reason,
            "Interpretation": PLAIN[dec],
        })
    return pd.DataFrame(rows)


def analysis_notes(n_students):
    notes = []
    g = group_size(n_students)
    notes.append(f"Upper and lower groups each contain {g} student(s) "
                 f"(27% of {n_students}, minimum 1).")
    if n_students < 30:
        notes.append("With fewer than 30 students, p and D are unstable. "
                     "Treat decisions as indicative, not final.")
    return notes
