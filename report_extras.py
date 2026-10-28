"""
Extra reporting features for the Item Analysis app:

* compute_score_distribution() - bins student scores for the chart
* create_pdf_report()          - builds a shareable PDF report
"""

import math
from datetime import date
from enum import Enum
from io import BytesIO
from statistics import median
from xml.sax.saxutils import escape

from reportlab.graphics.charts.barcharts import VerticalBarChart
from reportlab.graphics.shapes import Drawing, String
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)


# ============================================================
# HELPERS
# ============================================================

def _get(obj, key, default=None):

    if isinstance(obj, dict):
        return obj.get(key, default)

    return getattr(obj, key, default)


def _plain(value):

    if isinstance(value, Enum):
        return value.value

    return value


def _num(value, default=0.0):

    try:
        number = float(value)
    except (TypeError, ValueError):
        return default

    if math.isnan(number) or math.isinf(number):
        return default

    return number


# ============================================================
# SCORE DISTRIBUTION
# ============================================================

def compute_score_distribution(results, max_bars=21):
    """
    Group student scores into bins for a histogram.

    Returns a dict:
        {
          "bins":   [(label, count), ...]  # in score order
          "mean":   float,
          "median": float,
          "total_questions": int,
          "bin_width": int,
        }

    One bar per score (0..N) when the test has up to `max_bars - 1`
    questions; otherwise scores are grouped into equal-width ranges
    so the chart stays readable.
    """

    students = _get(results, "students", []) or []
    summary = _get(results, "summary", {}) or {}

    total_questions = int(
        _num(_get(summary, "total_questions", 0))
    )

    scores = [
        int(_num(_get(s, "score", 0)))
        for s in students
    ]

    if total_questions <= 0:
        total_questions = max(scores) if scores else 0

    bin_width = max(
        1,
        math.ceil((total_questions + 1) / max_bars)
    )

    bins = []

    start = 0

    while start <= total_questions:

        end = min(start + bin_width - 1, total_questions)

        label = (
            str(start)
            if start == end
            else f"{start}-{end}"
        )

        count = sum(
            1 for score in scores
            if start <= score <= end
        )

        bins.append((label, count))

        start += bin_width

    return {
        "bins": bins,
        "mean": (
            sum(scores) / len(scores)
            if scores else 0.0
        ),
        "median": float(median(scores)) if scores else 0.0,
        "total_questions": total_questions,
        "bin_width": bin_width,
    }


# ============================================================
# PDF REPORT
# ============================================================

_NAVY = colors.HexColor("#1F3A5F")
_LIGHT = colors.HexColor("#EEF2F7")
_GRID = colors.HexColor("#C9D3E0")

_REC_COLORS = {
    "RETAIN": colors.HexColor("#1B7F3B"),
    "REVIEW": colors.HexColor("#B7791F"),
    "REVISE": colors.HexColor("#C05621"),
    "DISCARD": colors.HexColor("#C53030"),
}


def _styles():

    base = getSampleStyleSheet()

    return {
        "title": ParagraphStyle(
            "ReportTitle",
            parent=base["Title"],
            fontSize=20,
            textColor=_NAVY,
            spaceAfter=4,
        ),
        "subtitle": ParagraphStyle(
            "ReportSubtitle",
            parent=base["Normal"],
            fontSize=9,
            textColor=colors.grey,
            alignment=1,
            spaceAfter=10,
        ),
        "h2": ParagraphStyle(
            "ReportH2",
            parent=base["Heading2"],
            fontSize=13,
            textColor=_NAVY,
            spaceBefore=10,
            spaceAfter=6,
        ),
        "body": ParagraphStyle(
            "ReportBody",
            parent=base["Normal"],
            fontSize=9,
            leading=12,
        ),
        "note": ParagraphStyle(
            "ReportNote",
            parent=base["Normal"],
            fontSize=8,
            textColor=colors.grey,
            leading=10,
        ),
    }


def _table(data, col_widths, header=True, align_center_from=0):

    table = Table(data, colWidths=col_widths, repeatRows=1 if header else 0)

    style = [
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("GRID", (0, 0), (-1, -1), 0.4, _GRID),
        ("ALIGN", (align_center_from, 0), (-1, -1), "CENTER"),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]

    if header:
        style += [
            ("BACKGROUND", (0, 0), (-1, 0), _NAVY),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            (
                "ROWBACKGROUNDS",
                (0, 1),
                (-1, -1),
                [colors.white, _LIGHT],
            ),
        ]

    table.setStyle(TableStyle(style))

    return table


def _distribution_chart(dist, width, height=170):

    drawing = Drawing(width, height)

    labels = [label for label, _ in dist["bins"]]
    counts = [count for _, count in dist["bins"]]

    chart = VerticalBarChart()
    chart.x = 35
    chart.y = 30
    chart.width = width - 50
    chart.height = height - 60
    chart.data = [counts]
    chart.categoryAxis.categoryNames = labels
    chart.categoryAxis.labels.fontSize = 7
    chart.categoryAxis.labels.boxAnchor = "n"
    chart.valueAxis.valueMin = 0
    chart.valueAxis.valueMax = max(max(counts, default=0), 1) + 1
    chart.valueAxis.valueStep = (
        1 if max(counts, default=0) <= 10
        else math.ceil(max(counts) / 10)
    )
    chart.valueAxis.labels.fontSize = 7
    chart.bars[0].fillColor = colors.HexColor("#3B6EA8")
    chart.bars[0].strokeColor = colors.white
    chart.barLabelFormat = lambda v: "" if not v else "%d" % v
    chart.barLabels.fontSize = 7
    chart.barLabels.nudge = 6

    drawing.add(chart)

    drawing.add(
        String(
            width / 2,
            8,
            "Score (number of correct answers)",
            fontSize=8,
            textAnchor="middle",
        )
    )

    return drawing


def create_pdf_report(results):
    """
    Build the complete item analysis report as PDF bytes.

    `results` is the same dict used by create_excel_report()
    (summary / items / students / exam_info).
    """

    buffer = BytesIO()

    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=15 * mm,
        rightMargin=15 * mm,
        topMargin=15 * mm,
        bottomMargin=15 * mm,
        title="Item Analysis Report",
    )

    usable_width = A4[0] - 30 * mm
    styles = _styles()
    story = []

    summary = _get(results, "summary", {}) or {}
    items = _get(results, "items", []) or []
    exam_info = _get(results, "exam_info", {}) or {}

    # --------------------------------------------------------
    # TITLE + EXAM INFORMATION
    # --------------------------------------------------------

    story.append(Paragraph("Item Analysis Report", styles["title"]))
    story.append(
        Paragraph(
            f"Generated on {date.today().strftime('%d %B %Y')}",
            styles["subtitle"],
        )
    )

    info_rows = [
        [
            "Examination Name",
            str(_get(exam_info, "Examination Name", "") or "-"),
        ],
        [
            "Examination Year",
            str(_get(exam_info, "Examination Year", "") or "-"),
        ],
        ["Class", str(_get(exam_info, "Class", "") or "-")],
        ["Subject", str(_get(exam_info, "Subject", "") or "-")],
    ]

    info_table = Table(
        [
            [
                Paragraph(f"<b>{escape(k)}</b>", styles["body"]),
                Paragraph(escape(v), styles["body"]),
            ]
            for k, v in info_rows
        ],
        colWidths=[45 * mm, usable_width - 45 * mm],
    )
    info_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (0, -1), _LIGHT),
                ("GRID", (0, 0), (-1, -1), 0.4, _GRID),
                ("TOPPADDING", (0, 0), (-1, -1), 3),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ]
        )
    )
    story.append(info_table)

    # --------------------------------------------------------
    # COHORT SUMMARY
    # --------------------------------------------------------

    total_questions = int(_num(_get(summary, "total_questions", 0)))

    story.append(Paragraph("Cohort at a glance", styles["h2"]))

    summary_rows = [
        ["Total Students", "Evaluated Items", "Mean Score"],
        [
            str(int(_num(_get(summary, "total_students", 0)))),
            str(total_questions),
            f"{_num(_get(summary, 'mean_score', 0)):.2f} / "
            f"{total_questions}",
        ],
        ["Std. Deviation", "Minimum Score", "Maximum Score"],
        [
            f"{_num(_get(summary, 'std_score', 0)):.2f}",
            str(int(_num(_get(summary, 'min_score', 0)))),
            str(int(_num(_get(summary, 'max_score', 0)))),
        ],
    ]

    third = usable_width / 3

    summary_table = Table(summary_rows, colWidths=[third] * 3)
    summary_table.setStyle(
        TableStyle(
            [
                ("GRID", (0, 0), (-1, -1), 0.4, _GRID),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("BACKGROUND", (0, 0), (-1, 0), _LIGHT),
                ("BACKGROUND", (0, 2), (-1, 2), _LIGHT),
                ("FONTSIZE", (0, 0), (-1, -1), 8),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTNAME", (0, 2), (-1, 2), "Helvetica-Bold"),
                ("FONTSIZE", (0, 1), (-1, 1), 13),
                ("FONTSIZE", (0, 3), (-1, 3), 13),
                ("TEXTCOLOR", (0, 1), (-1, 1), _NAVY),
                ("TEXTCOLOR", (0, 3), (-1, 3), _NAVY),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )
    story.append(summary_table)

    # --------------------------------------------------------
    # SCORE DISTRIBUTION
    # --------------------------------------------------------

    dist = compute_score_distribution(results)

    story.append(Paragraph("Score distribution", styles["h2"]))
    story.append(_distribution_chart(dist, usable_width))
    story.append(
        Paragraph(
            f"Mean: {dist['mean']:.2f} &nbsp;|&nbsp; "
            f"Median: {dist['median']:.1f} &nbsp;|&nbsp; "
            f"Out of {dist['total_questions']} questions",
            styles["note"],
        )
    )

    # --------------------------------------------------------
    # RECOMMENDATION SUMMARY
    # --------------------------------------------------------

    counts = {key: 0 for key in _REC_COLORS}

    for item in items:
        rec = str(_plain(_get(item, "recommendation", ""))).upper()
        if rec in counts:
            counts[rec] += 1

    story.append(Paragraph("Item recommendations", styles["h2"]))

    rec_table = _table(
        [list(counts.keys()), [str(v) for v in counts.values()]],
        [usable_width / 4] * 4,
    )
    for col, key in enumerate(counts):
        rec_table.setStyle(
            TableStyle(
                [
                    (
                        "TEXTCOLOR",
                        (col, 1),
                        (col, 1),
                        _REC_COLORS[key],
                    ),
                    ("FONTNAME", (col, 1), (col, 1), "Helvetica-Bold"),
                    ("FONTSIZE", (col, 1), (col, 1), 12),
                ]
            )
        )
    story.append(rec_table)

    # --------------------------------------------------------
    # ITEM ANALYSIS TABLE
    # --------------------------------------------------------

    story.append(Paragraph("Item-by-item analysis", styles["h2"]))

    header = [
        "Q",
        "Key",
        "Correct",
        "Difficulty",
        "Discrim.",
        "Distractor\nEff.",
        "Omitted",
        "Recommendation",
    ]

    rows = [header]
    rec_cells = []

    for index, item in enumerate(items, start=1):

        rec = str(_plain(_get(item, "recommendation", ""))).upper()

        rows.append(
            [
                str(_get(item, "question_number", index)),
                str(_get(item, "correct_answer", "")),
                f"{int(_num(_get(item, 'correct_count', 0)))}/"
                f"{int(_num(_get(item, 'total_students', 0)))}",
                f"{_num(_get(item, 'difficulty', 0)):.2f} "
                f"({_get(item, 'difficulty_status', '')})",
                f"{_num(_get(item, 'discrimination', 0)):.2f} "
                f"({_get(item, 'discrimination_status', '')})",
                f"{_num(_get(item, 'distractor_efficiency', 0)):.0f}%",
                str(int(_num(_get(item, "omitted_count", 0)))),
                rec,
            ]
        )

        rec_cells.append((len(rows) - 1, rec))

    widths = [
        9 * mm,
        10 * mm,
        18 * mm,
        32 * mm,
        32 * mm,
        20 * mm,
        16 * mm,
        usable_width - (9 + 10 + 18 + 32 + 32 + 20 + 16) * mm,
    ]

    item_table = _table(rows, widths)

    for row_index, rec in rec_cells:
        item_table.setStyle(
            TableStyle(
                [
                    (
                        "TEXTCOLOR",
                        (7, row_index),
                        (7, row_index),
                        _REC_COLORS.get(rec, colors.black),
                    ),
                    (
                        "FONTNAME",
                        (7, row_index),
                        (7, row_index),
                        "Helvetica-Bold",
                    ),
                ]
            )
        )

    story.append(item_table)

    # --------------------------------------------------------
    # OPTION BREAKDOWN
    # --------------------------------------------------------

    story.append(PageBreak())
    story.append(Paragraph("Option breakdown", styles["h2"]))
    story.append(
        Paragraph(
            "Number of students choosing each option. The correct "
            "answer is shown in bold; options marked * were chosen "
            "too rarely to be functional distractors.",
            styles["note"],
        )
    )
    story.append(Spacer(1, 4))

    option_letters = []

    for item in items:
        for opt in _get(item, "option_breakdown", []) or []:
            letter = str(_get(opt, "option", ""))
            if letter and letter not in option_letters:
                option_letters.append(letter)

    option_letters.sort()

    opt_rows = [["Q"] + option_letters + ["Omitted"]]
    bold_cells = []
    flag_cells = []

    for index, item in enumerate(items, start=1):

        by_letter = {
            str(_get(o, "option", "")): o
            for o in _get(item, "option_breakdown", []) or []
        }

        row = [str(_get(item, "question_number", index))]

        for col, letter in enumerate(option_letters, start=1):

            opt = by_letter.get(letter)

            if opt is None:
                row.append("-")
                continue

            text = (
                f"{int(_num(_get(opt, 'count', 0)))} "
                f"({_num(_get(opt, 'percentage', 0)):.0f}%)"
            )

            if _get(opt, "is_correct", False):
                bold_cells.append((col, len(opt_rows)))
            elif not _get(opt, "is_functional", True):
                text += " *"
                flag_cells.append((col, len(opt_rows)))

            row.append(text)

        row.append(str(int(_num(_get(item, "omitted_count", 0)))))
        opt_rows.append(row)

    opt_width = (usable_width - 12 * mm - 18 * mm) / max(
        len(option_letters), 1
    )

    opt_table = _table(
        opt_rows,
        [12 * mm] + [opt_width] * len(option_letters) + [18 * mm],
    )

    for col, row in bold_cells:
        opt_table.setStyle(
            TableStyle(
                [
                    ("FONTNAME", (col, row), (col, row), "Helvetica-Bold"),
                    (
                        "BACKGROUND",
                        (col, row),
                        (col, row),
                        colors.HexColor("#D8F0DF"),
                    ),
                ]
            )
        )

    for col, row in flag_cells:
        opt_table.setStyle(
            TableStyle(
                [
                    (
                        "TEXTCOLOR",
                        (col, row),
                        (col, row),
                        colors.HexColor("#C05621"),
                    ),
                ]
            )
        )

    story.append(opt_table)

    # --------------------------------------------------------
    # PAGE NUMBERS
    # --------------------------------------------------------

    def _footer(canvas, document):
        canvas.saveState()
        canvas.setFont("Helvetica", 8)
        canvas.setFillColor(colors.grey)
        canvas.drawCentredString(
            A4[0] / 2, 8 * mm, f"Page {document.page}"
        )
        canvas.restoreState()

    doc.build(story, onFirstPage=_footer, onLaterPages=_footer)

    return buffer.getvalue()
