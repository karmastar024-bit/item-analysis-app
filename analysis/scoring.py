"""Convert raw responses into 0/1 scores for selected-response and
short constructed-response items. Missing/blank = incorrect (0)."""
import re
import string
import numpy as np
import pandas as pd

TRUE_WORDS = {"t": "T", "true": "T", "1": "T", "yes": "T"}
FALSE_WORDS = {"f": "F", "false": "F", "0": "F", "no": "F"}
TF_MAP = {**TRUE_WORDS, **FALSE_WORDS}


def _blank(v):
    return v is None or (isinstance(v, float) and np.isnan(v)) or str(v).strip() == ""


def normalize_tf(v):
    """-> 'T', 'F' or None (blank). Raises nothing; invalid -> '?'."""
    if _blank(v):
        return None
    return TF_MAP.get(str(v).strip().lower(), "?")


def normalize_text(v, ignore_case=True, strip_punct=False, collapse_space=True):
    if _blank(v):
        return ""
    s = str(v).strip()
    if ignore_case:
        s = s.casefold()
    if strip_punct:
        s = s.translate(str.maketrans("", "", string.punctuation))
    if collapse_space:
        s = re.sub(r"\s+", " ", s)
    return s.strip()


def split_accepted(cell):
    """'Paro | paro dzong' -> ['Paro', 'paro dzong']"""
    return [a.strip() for a in str(cell).split("|") if a.strip()]


def score_true_false(resp: pd.DataFrame, key: dict):
    k = {c: normalize_tf(key[c]) for c in key}
    out = pd.DataFrame(index=resp.index)
    for c in resp.columns:
        out[c] = [int(normalize_tf(v) == k[c]) for v in resp[c]]
    return out


def score_fill_blank(resp, accepted: dict, ignore_case=True,
                     strip_punct=False, collapse_space=True):
    """accepted: {item: [answer, alt, ...]}"""
    fn = lambda v: normalize_text(v, ignore_case, strip_punct, collapse_space)
    acc = {c: {fn(a) for a in accepted[c] if fn(a)} for c in accepted}
    out = pd.DataFrame(index=resp.index)
    for c in resp.columns:
        out[c] = [int(fn(v) in acc[c] and fn(v) != "") for v in resp[c]]
    return out


def score_matching(resp, key: dict, ignore_case=True):
    """Each prompt is ONE item worth 1 point: correct iff the chosen
    answer equals the key (case-insensitive by default)."""
    fn = lambda v: normalize_text(v, ignore_case, False, True)
    out = pd.DataFrame(index=resp.index)
    for c in resp.columns:
        out[c] = [int(fn(v) != "" and fn(v) == fn(key[c])) for v in resp[c]]
    return out
