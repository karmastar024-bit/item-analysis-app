"""Read uploads in memory and build downloadable reports."""
from io import BytesIO
import pandas as pd

MAX_MB = 10


def read_upload(uploaded):
    """Return a DataFrame of strings (blank cells -> NaN). Raises ValueError
    with a teacher-friendly message on any problem."""
    if uploaded is None:
        raise ValueError("No file was uploaded.")
    name = uploaded.name.lower()
    raw = uploaded.getvalue()
    if len(raw) == 0:
        raise ValueError("The file is empty.")
    if len(raw) > MAX_MB * 1024 * 1024:
        raise ValueError(f"The file is larger than {MAX_MB} MB. Please upload a smaller file.")
    try:
        if name.endswith(".csv"):
            for enc in ("utf-8-sig", "latin-1"):
                try:
                    df = pd.read_csv(BytesIO(raw), dtype=str, encoding=enc,
                                     keep_default_na=True, skip_blank_lines=True)
                    break
                except UnicodeDecodeError:
                    continue
        elif name.endswith(".xlsx"):
            df = pd.read_excel(BytesIO(raw), dtype=str, engine="openpyxl")
        else:
            raise ValueError("Unsupported file type. Please upload a .csv or .xlsx file.")
    except pd.errors.EmptyDataError:
        raise ValueError("The file contains no data.")
    except ValueError:
        raise
    except Exception:
        raise ValueError("The file could not be read. Check that it is a valid, "
                         "unprotected .csv or .xlsx file and matches the Data Format Guide.")
    df = df.dropna(how="all").dropna(axis=1, how="all")
    df.columns = [str(c).strip() for c in df.columns]
    if df.empty:
        raise ValueError("The file contains headers but no student rows.")
    return df


def df_to_csv_bytes(df):
    return df.to_csv(index=False).encode("utf-8-sig")


def df_to_excel_bytes(sheets: dict):
    """sheets: {sheet_name: DataFrame}"""
    buf = BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as xw:
        for name, d in sheets.items():
            d.to_excel(xw, sheet_name=name[:31], index=False)
            ws = xw.sheets[name[:31]]
            for col in ws.columns:
                width = min(60, max(len(str(c.value)) if c.value is not None else 0 for c in col) + 2)
                ws.column_dimensions[col[0].column_letter].width = width
    return buf.getvalue()


def build_pdf_report(title, meta: dict, table: pd.DataFrame, notes: list,
                     methodology: list, charts_png: list = None):
    """Compact PDF: assessment info, results table, decisions, method, notes."""
    from xml.sax.saxutils import escape
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.lib.units import mm
    from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer, Table,
                                    TableStyle, Image, PageBreak)
    buf = BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=landscape(A4), leftMargin=12*mm,
                            rightMargin=12*mm, topMargin=12*mm, bottomMargin=12*mm,
                            title=title, author="Item Analyzer")
    ss = getSampleStyleSheet(); small = ss["BodyText"].clone("s", fontSize=8, leading=10)
    story = [Paragraph(escape(title), ss["Title"]),
             Paragraph("Item Analyzer • Made for Educators in Bhutan", ss["Normal"]), Spacer(1, 6)]
    for k, v in meta.items():
        story.append(Paragraph(f"<b>{escape(str(k))}:</b> {escape(str(v))}", ss["Normal"]))
    story += [Spacer(1, 8), Paragraph("Results", ss["Heading2"])]
    show = table.drop(columns=[c for c in ("Interpretation",) if c in table.columns])
    data = [[Paragraph(f"<b>{escape(str(c))}</b>", small) for c in show.columns]]
    for _, r in show.iterrows():
        data.append([Paragraph(escape("" if pd.isna(v) else str(v)), small) for v in r])
    tbl = Table(data, repeatRows=1)
    tbl.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#DDE6F0")),
                             ("GRID", (0, 0), (-1, -1), .25, colors.grey),
                             ("VALIGN", (0, 0), (-1, -1), "TOP")]))
    story.append(tbl)
    for png in charts_png or []:
        story += [Spacer(1, 8), Image(BytesIO(png), width=150*mm, height=80*mm)]
    story += [Spacer(1, 8), Paragraph("Methodology", ss["Heading2"])]
    story += [Paragraph("• " + escape(m), ss["Normal"]) for m in methodology]
    story += [Spacer(1, 6), Paragraph("Notes", ss["Heading2"])]
    story += [Paragraph("• " + escape(n), ss["Normal"]) for n in notes]
    doc.build(story)
    return buf.getvalue()
