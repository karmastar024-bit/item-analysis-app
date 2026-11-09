"""Normalize assessment headers and key rows without changing item values."""
import pandas as pd


def assessment_table(frame):
    """Accept KEY/MAX above the header, as well as legacy rows below it."""
    if frame.empty:
        raise ValueError("The file contains no data.")
    frame = frame.fillna("").astype(str).apply(lambda col: col.str.strip())
    first = frame.iloc[:, 0].str.casefold()
    headers = frame.index[first.isin(["student id", "studentid", "student_id", "id", "student"])].tolist()
    if len(headers) > 1:
        raise ValueError("Keep exactly one header row beginning with Student ID.")
    h = headers[0] if headers else frame.index[0]
    labels = frame.loc[h].tolist()
    while labels and not labels[-1]:
        labels.pop()
    special = frame.loc[(frame.index < h) & first.isin(["key", "max"])]
    body = pd.concat([special, frame.loc[frame.index > h]])
    body = body.loc[body.ne("").any(axis=1)]
    if body.iloc[:, len(labels):].ne("").any().any():
        raise ValueError("Some entries have no column header. Add a header for every item.")
    body = body.iloc[:, :len(labels)].copy()
    body.columns = labels
    return body.reset_index(drop=True)
