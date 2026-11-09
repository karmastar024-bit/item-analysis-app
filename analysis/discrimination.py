"""Discrimination index (D).

Upper-lower method (Kelley): groups are the top and bottom 27% of
students ranked on total score (at least 1 student per group).

Binary  : D = (U - L) / g          U, L = correct in upper / lower group
Partial : D = (mean_upper - mean_lower) / max_score   (range -1 .. +1)
Also provided for partial credit: corrected item-total correlation
(Pearson r between the item and the total of the OTHER items).
"""
import numpy as np

GROUP_FRACTION = 0.27


def group_size(n):
    return max(1, int(n * GROUP_FRACTION))


def upper_lower_indices(totals):
    """Indices of upper and lower groups (stable sort, so ties are
    broken by original row order, deterministically)."""
    totals = np.asarray(totals, dtype=float)
    order = np.argsort(-totals, kind="stable")
    g = group_size(len(totals))
    return order[:g], order[-g:]


def discrimination_ul(item_scores, totals, max_score=1.0):
    x = np.asarray(item_scores, dtype=float)
    upper, lower = upper_lower_indices(totals)
    if len(x) < 2 or not max_score:
        return float("nan")
    return float((np.nanmean(x[upper]) - np.nanmean(x[lower])) / max_score)


def corrected_item_total_r(item_scores, totals):
    """Pearson r between item and (total - item). NaN if undefined
    (constant item, constant rest-score, or fewer than 3 students)."""
    x = np.asarray(item_scores, dtype=float)
    rest = np.asarray(totals, dtype=float) - x
    if len(x) < 3 or np.nanstd(x) == 0 or np.nanstd(rest) == 0:
        return float("nan")
    return float(np.corrcoef(x, rest)[0, 1])


def discrimination_label(d):
    if np.isnan(d):
        return "Not available"
    if d < 0:
        return "Negative"
    if d < 0.20:
        return "Poor"
    if d < 0.30:
        return "Fair"
    return "Good"
