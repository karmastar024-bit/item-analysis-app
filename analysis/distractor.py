"""Distractor efficiency (DE) - MCQ ONLY.

A distractor is functional if chosen by >= 5% of ALL students.
DE = functional distractors / total distractors x 100.
Matches the rule already used in item_analyzer.py.
"""
NON_FUNCTIONAL_THRESHOLD = 0.05


def distractor_efficiency(option_counts, correct, n_students):
    """option_counts: {option: count}. Returns (DE %, details list)."""
    details, functional, total = [], 0, 0
    for opt, cnt in option_counts.items():
        share = cnt / n_students if n_students else 0.0
        is_correct = opt == correct
        ok = True if is_correct else share >= NON_FUNCTIONAL_THRESHOLD
        if not is_correct:
            total += 1
            functional += int(ok)
        details.append({"option": opt, "count": int(cnt),
                        "percent": round(share * 100, 2),
                        "is_correct": is_correct, "functional": ok})
    de = (functional / total * 100) if total else 0.0
    return round(de, 2), details
