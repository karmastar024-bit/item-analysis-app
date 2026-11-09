"""Difficulty index (p).

Concept : how easy an item was for the group.
Binary  : p = (number correct) / (number of students)
Partial : p = (mean item score) / (maximum possible item score)
Edge    : no students, or max score <= 0  ->  NaN (caller must handle).
"""
import numpy as np

EASY_CUTOFF = 0.80
HARD_CUTOFF = 0.20


def difficulty_binary(item_scores):
    """item_scores: array-like of 0/1 (NaN = missing, ignored)."""
    x = np.asarray(item_scores, dtype=float)
    x = x[~np.isnan(x)]
    return float("nan") if x.size == 0 else float(x.sum() / x.size)


def difficulty_normalized(item_scores, max_score):
    """Mean score as a proportion of the maximum possible score."""
    x = np.asarray(item_scores, dtype=float)
    x = x[~np.isnan(x)]
    if x.size == 0 or not max_score or max_score <= 0:
        return float("nan")
    return float(x.mean() / max_score)


def difficulty_label(p):
    if np.isnan(p):
        return "Not available"
    if p < HARD_CUTOFF:
        return "Very Difficult"
    if p > EASY_CUTOFF:
        return "Too Easy"
    return "Ideal"
