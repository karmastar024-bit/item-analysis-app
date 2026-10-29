"""Altair charts for the UI + matplotlib PNGs for the PDF report."""
from io import BytesIO
import altair as alt
import numpy as np
import pandas as pd

COLORS = {"RETAIN": "#2E7D5B", "REVIEW": "#D9A21B", "REVISE": "#E07B39",
          "DISCARD": "#C0392B", "NOT AVAILABLE": "#8A94A6"}
NAVY = "#1F3A5F"


def _hist(df, col, title, bins, domain=None, x_title=None):
    x = alt.X(f"{col}:Q", bin=alt.Bin(maxbins=bins), title=x_title or title)
    if domain:
        x = alt.X(f"{col}:Q", bin=alt.Bin(extent=domain, maxbins=bins), title=x_title or title,
                  scale=alt.Scale(domain=domain))
    return (alt.Chart(df.dropna(subset=[col])).mark_bar(color=NAVY)
            .encode(x=x, y=alt.Y("count()", title="Number of items"),
                    tooltip=[alt.Tooltip("count()", title="Items")])
            .properties(title=title, height=220))


def difficulty_hist(df, col):
    return _hist(df, col, "Difficulty distribution", 10, [0, 1], "Difficulty (p)")


def discrimination_hist(df, col):
    return _hist(df, col, "Discrimination distribution", 10, [-1, 1], "Discrimination (D)")


def de_hist(df, col="Distractor Efficiency (%)"):
    return _hist(df, col, "Distractor efficiency distribution", 5, [0, 100], "DE (%)")


def decision_bar(df):
    order = ["RETAIN", "REVIEW", "REVISE", "DISCARD", "NOT AVAILABLE"]
    c = df["Decision"].value_counts().reindex(order, fill_value=0).reset_index()
    c.columns = ["Decision", "Items"]; c = c[c["Items"] > 0]
    return (alt.Chart(c).mark_bar().encode(
        x=alt.X("Decision:N", sort=order, title=None, axis=alt.Axis(labelAngle=0)),
        y=alt.Y("Items:Q", title="Number of items", axis=alt.Axis(tickMinStep=1)),
        color=alt.Color("Decision:N", scale=alt.Scale(domain=list(COLORS), range=list(COLORS.values())),
                        legend=None), tooltip=["Decision", "Items"])
        .properties(title="Decision distribution", height=220))


def item_scatter(df, pcol, dcol):
    """Difficulty vs discrimination with the decision thresholds drawn."""
    base = alt.Chart(df).mark_circle(size=140).encode(
        x=alt.X(f"{pcol}:Q", scale=alt.Scale(domain=[0, 1]), title="Difficulty (p)"),
        y=alt.Y(f"{dcol}:Q", title="Discrimination (D)"),
        color=alt.Color("Decision:N", scale=alt.Scale(domain=list(COLORS), range=list(COLORS.values()))),
        tooltip=["Item", pcol, dcol, "Decision"])
    rules = (alt.Chart(pd.DataFrame({"x": [0.2, 0.8]})).mark_rule(strokeDash=[4, 4], color="#999").encode(x="x:Q")
             + alt.Chart(pd.DataFrame({"y": [0.2]})).mark_rule(strokeDash=[4, 4], color="#999").encode(y="y:Q"))
    return (base + rules).properties(title="Each item: difficulty vs discrimination", height=300)


def score_hist(values, title="Distribution of total scores", x_title="Total score"):
    d = pd.DataFrame({"score": values})
    n = max(5, min(20, int(np.sqrt(len(d))) + 3))
    return (alt.Chart(d).mark_bar(color=NAVY).encode(
        x=alt.X("score:Q", bin=alt.Bin(maxbins=n), title=x_title),
        y=alt.Y("count()", title="Students")).properties(title=title, height=260))


def boxplot(values, title="Box plot of total scores", label="Scores"):
    d = pd.DataFrame({"score": values, "g": label})
    return (alt.Chart(d).mark_boxplot(color=NAVY, extent=1.5).encode(
        y=alt.Y("score:Q", title="Score"), x=alt.X("g:N", title=None))
        .properties(title=title, height=260, width=160))


def grouped_boxplot(groups: dict, title="Box plot by group"):
    d = pd.concat([pd.DataFrame({"score": v, "group": k}) for k, v in groups.items()])
    return (alt.Chart(d).mark_boxplot(color=NAVY, extent=1.5).encode(
        x=alt.X("group:N", title=None), y=alt.Y("score:Q", title="Score"))
        .properties(title=title, height=260))


def item_score_bars(scores: pd.Series, max_score):
    vc = scores.fillna(0).value_counts().sort_index().reset_index(); vc.columns = ["Score", "Students"]
    return (alt.Chart(vc).mark_bar(color=NAVY).encode(
        x=alt.X("Score:O", title=f"Score awarded (max {max_score:g})"),
        y=alt.Y("Students:Q", axis=alt.Axis(tickMinStep=1))).properties(height=200))


def pdf_pngs(df, pcol, dcol):
    """Small matplotlib PNGs for the PDF report (no browser needed)."""
    import matplotlib; matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    out = []
    fig, ax = plt.subplots(1, 3, figsize=(10, 3.2))
    ax[0].hist(df[pcol].dropna(), bins=np.linspace(0, 1, 11), color=NAVY); ax[0].set_title("Difficulty (p)")
    ax[1].hist(df[dcol].dropna(), bins=np.linspace(-1, 1, 11), color=NAVY); ax[1].set_title("Discrimination (D)")
    c = df["Decision"].value_counts()
    ax[2].bar(c.index, c.values, color=[COLORS.get(k, NAVY) for k in c.index]); ax[2].set_title("Decisions")
    for a in ax: a.spines[["top", "right"]].set_visible(False)
    fig.tight_layout(); buf = BytesIO(); fig.savefig(buf, format="png", dpi=150); plt.close(fig)
    out.append(buf.getvalue()); return out
