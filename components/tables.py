import streamlit as st
import pandas as pd
from utils.file_handlers import df_to_csv_bytes, df_to_excel_bytes

BADGE = {"RETAIN": "🟢", "REVIEW": "🟡", "REVISE": "🟠", "DISCARD": "🔴", "NOT AVAILABLE": "⚪"}


def decision_metrics(df):
    cols = st.columns(4)
    for col, d in zip(cols, ["RETAIN", "REVIEW", "REVISE", "DISCARD"]):
        col.metric(f"{BADGE[d]} {d.title()}", int((df["Decision"] == d).sum()))


def results_table(df, hide=("Interpretation",)):
    show = df.drop(columns=[c for c in hide if c in df.columns]).copy()
    show["Decision"] = show["Decision"].map(lambda d: f"{BADGE.get(d, '')} {d}")
    st.dataframe(show, hide_index=True, width="stretch",
                 column_config={"Reason": st.column_config.TextColumn(width="large")})


def downloads(df, base_name, extra_sheets=None, pdf_bytes=None, key=""):
    sheets = {"Item Analysis": df}; sheets.update(extra_sheets or {})
    cols = st.columns(3 if pdf_bytes else 2)
    cols[0].download_button("⬇️ CSV", df_to_csv_bytes(df), f"{base_name}.csv", "text/csv",
                            width="stretch", key=f"csv_{key}")
    cols[1].download_button("⬇️ Excel", df_to_excel_bytes(sheets), f"{base_name}.xlsx",
                            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                            width="stretch", key=f"xlsx_{key}")
    if pdf_bytes:
        cols[2].download_button("⬇️ PDF report", pdf_bytes, f"{base_name}.pdf", "application/pdf",
                                width="stretch", key=f"pdf_{key}")


def item_cards(df):
    """Per-item plain-language explanation (expanders)."""
    for _, r in df.iterrows():
        with st.expander(f"{BADGE.get(r['Decision'], '')} {r['Item']} — {r['Decision']}"):
            st.write(r["Reason"])
            st.caption(r["Interpretation"])
