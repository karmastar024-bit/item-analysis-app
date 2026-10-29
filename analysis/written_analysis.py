"""Constructed-response (short answer / long answer / essay) analysis.

Scores are NOT binary. Methodology:
 Difficulty      p = mean item score / max item score
                 (normalized difficulty; "proportion of maximum score")
 Discrimination  D = (mean upper - mean lower) / max score  (27% groups,
                 ranked by total score). Same 0.20 cut-off as binary items.
 Supplementary   corrected item-total correlation (r_it).
"""
import numpy as np
import pandas as pd
from .difficulty import difficulty_normalized, difficulty_label
from .discrimination import (discrimination_ul, discrimination_label,
                             corrected_item_total_r)
from .decision import decide, PLAIN


def analyze_written(scores: pd.DataFrame, max_scores: dict) -> pd.DataFrame:
    n = len(scores)
    # Missing scores: treated as 0 for totals, but reported in 'Missing'.
    filled = scores.fillna(0)
    totals = filled.sum(axis=1).to_numpy(dtype=float)
    rows = []
    for c in scores.columns:
        m = float(max_scores[c])
        x = filled[c].to_numpy(dtype=float)
        p = difficulty_normalized(x, m)
        d = discrimination_ul(x, totals, m) if n >= 2 else float("nan")
        r = corrected_item_total_r(x, totals) if scores.shape[1] > 1 else float("nan")
        dec, reason = decide(p, d)
        rows.append({
            "Item": c, "Max Score": m,
            "Mean Score": round(float(x.mean()), 2),
            "Difficulty (p = mean/max)": round(p, 2),
            "Difficulty Level": difficulty_label(p),
            "Discrimination (D)": round(d, 2) if not np.isnan(d) else np.nan,
            "Discrimination Level": discrimination_label(d),
            "Item-Total r": round(r, 2) if not np.isnan(r) else np.nan,
            "Missing Scores": int(scores[c].isna().sum()),
            "Decision": dec, "Reason": reason, "Interpretation": PLAIN[dec],
        })
    return pd.DataFrame(rows)


def score_distribution(scores: pd.Series, max_score: float, bins=5):
    """Counts of students per band of the maximum score."""
    edges = np.linspace(0, max_score, bins + 1)
    cut = pd.cut(scores.fillna(0), bins=edges, include_lowest=True)
    return cut.value_counts().sort_index()
