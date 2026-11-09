"""Decision rules shared by every item type.

Order matters (first match wins):
 1 DISCARD : D < 0, or p == 0, or p == 1, or (MCQ only) DE == 0 %
 2 REVISE  : D < 0.20 AND (p < 0.20 OR p > 0.80)
 3 REVIEW  : D < 0.20 OR p < 0.20 OR p > 0.80
 4 RETAIN  : otherwise
Raw (unrounded) values are used; rounding is for display only.
"""
import math

D_MIN = 0.20
P_LOW = 0.20
P_HIGH = 0.80


def _nan(x):
    return x is None or (isinstance(x, float) and math.isnan(x))


def decide(p, d, de=None):
    """Return (decision, reason). de=None means 'not applicable'."""
    if _nan(p) or _nan(d):
        return "NOT AVAILABLE", ("Difficulty or discrimination could not be "
                                 "computed (too little data or no variation).")
    hard, easy = p < P_LOW, p > P_HIGH
    weak = d < D_MIN
    ptxt = f"p = {p:.2f}"
    dtxt = f"D = {d:.2f}"

    discard = []
    if d < 0:
        discard.append(f"discrimination is negative ({dtxt}): stronger students did worse than weaker ones")
    if p == 0:
        discard.append("nobody scored on it (p = 0)")
    if p == 1:
        discard.append("everybody got full marks (p = 1)")
    if de is not None and de == 0:
        discard.append("no distractor is functioning (DE = 0%)")
    if discard:
        return "DISCARD", "DISCARD – " + "; ".join(discard) + "."

    dword = "high" if easy else "low"
    if weak and (hard or easy):
        return "REVISE", (f"REVISE – Difficulty is {dword} ({ptxt}) and "
                          f"discrimination is below 0.20 ({dtxt}).")
    if weak:
        return "REVIEW", f"REVIEW – Discrimination is below 0.20 ({dtxt})."
    if hard or easy:
        return "REVIEW", f"REVIEW – Difficulty is {dword} ({ptxt})."
    return "RETAIN", (f"RETAIN – Difficulty is acceptable ({ptxt}) and "
                      f"discrimination is adequate ({dtxt}).")


PLAIN = {
    "RETAIN": "The item works well. Keep it.",
    "REVIEW": "The item has one concern. Check the wording and the key before reuse.",
    "REVISE": "The item has two concerns. Rewrite it before reuse.",
    "DISCARD": "The item is not measuring what you intend. Do not reuse it as is.",
    "NOT AVAILABLE": "Not enough information to decide.",
}
