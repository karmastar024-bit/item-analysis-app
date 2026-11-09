"""Home dashboard: choose an assessment analysis."""
from html import escape

import streamlit as st
from components.navigation import go
from utils.translations import t


HOME_CSS = """
<style>
.ia-home-hero {
    position: relative; overflow: hidden; isolation: isolate;
    padding: 48px 44px; margin: 4px 0 32px; border-radius: 28px;
    background: linear-gradient(115deg, #101d3b 0%, #163c58 60%, #116c70 100%);
    color: #fff; box-shadow: 0 18px 45px #112c4420;
}
.ia-home-hero::after {
    content: ''; position: absolute; z-index: -1; width: 360px; height: 360px;
    right: -90px; top: -110px; border: 1px solid #ffffff30; border-radius: 50%;
    box-shadow: 0 0 0 42px #ffffff08, 0 0 0 84px #ffffff06, 0 0 0 126px #ffffff04;
}
.ia-home-eyebrow {font-size: 13px; font-weight: 800; letter-spacing: .17em; color: #9ce8df;}
.ia-home-hero h1 {font-size: clamp(36px, 5vw, 60px); font-weight: 850;
    line-height: 1.08; letter-spacing: -.04em; color: #fff; max-width: 750px;
    margin: 16px 0 20px; padding: 0;}
.ia-home-hero h1 span {color: #a4f0df;}
.ia-home-hero p {font-size: 19px; line-height: 1.6; max-width: 660px; margin: 0; color: #dce9f4;}
.ia-home-steps {display: flex; gap: 12px; flex-wrap: wrap; margin-top: 28px;}
.ia-home-steps span {padding: 8px 13px; border: 1px solid #ffffff30; border-radius: 100px;
    font-size: 13px; font-weight: 600; background: #ffffff0b; color: #eef8ff;}
.ia-home-heading {font-size: 29px; font-weight: 800; letter-spacing: -.025em; margin: 0 0 6px;}
.ia-home-hint {font-size: 16px; opacity: .75; margin: 0 0 24px;}
[class*="st-key-analysis_card_"] {
    --accent: #2459bc; --soft: #edf3ff; --ink: #162b50;
    background: linear-gradient(140deg, #fff 30%, var(--soft) 100%);
    border: 1px solid #dfe6ef; border-top: 5px solid var(--accent);
    border-radius: 22px; padding: 24px !important; margin-bottom: 20px;
    box-shadow: 0 6px 20px #12234208;
    transition: transform .18s ease, box-shadow .18s ease;
}
[class*="st-key-analysis_card_"]:hover {transform: translateY(-4px); box-shadow: 0 16px 30px #12234216;}
.st-key-analysis_card_tf {--accent: #117869; --soft: #e8f8f2;}
.st-key-analysis_card_fill {--accent: #8b4ab3; --soft: #f7eefc;}
.st-key-analysis_card_matching {--accent: #b45b16; --soft: #fff4e8;}
.st-key-analysis_card_written {--accent: #b04472; --soft: #fff0f5;}
.st-key-analysis_card_statistics {--accent: #426279; --soft: #edf4f8;}
.ia-select-top {display: flex; align-items: center; justify-content: space-between; gap: 12px;}
.ia-select-icon {display: grid; place-items: center; width: 58px; height: 58px;
    background: var(--soft); border-radius: 17px; font-size: 29px;}
.ia-select-tag {font-size: 11px; font-weight: 800; letter-spacing: .08em;
    text-transform: uppercase; color: var(--accent);}
.ia-select-card h3 {font-size: 28px; font-weight: 800; letter-spacing: -.035em;
    color: var(--ink); margin: 20px 0 10px; padding: 0; line-height: 1.2;}
.ia-select-card p {font-size: 16px; line-height: 1.6; color: #526178;
    min-height: 78px; margin: 0 0 10px;}
[class*="st-key-analysis_card_"] div[data-testid="stButton"] > button {
    min-height: 52px; border-radius: 12px; background: var(--accent); border: 2px solid var(--accent);
    color: white; box-shadow: none;
}
[class*="st-key-analysis_card_"] div[data-testid="stButton"] > button p {font-size: 17px; font-weight: 750;}
[class*="st-key-analysis_card_"] div[data-testid="stButton"] > button:hover {
    filter: brightness(.91); color: white; border-color: var(--accent);
}
[class*="st-key-analysis_card_"] div[data-testid="stButton"] > button:focus-visible {
    outline: 3px solid var(--accent); outline-offset: 4px;
}
@media (max-width: 700px) {
    .ia-home-hero {padding: 32px 24px; border-radius: 22px;}
    .ia-home-hero p {font-size: 17px;}
    .ia-home-heading {font-size: 25px;}
    .ia-select-card p {min-height: 0;}
    [class*="st-key-analysis_card_"] {padding: 22px !important;}
}
@media (prefers-reduced-motion: reduce) {
    [class*="st-key-analysis_card_"] {transition: none;}
    [class*="st-key-analysis_card_"]:hover {transform: none;}
}
</style>
"""

CHOICES = [
    ("mcq", "📝", "Multiple choice", "mcq",
     "See which questions work and which answer options need attention."),
    ("tf", "✔️", "Two options", "true_false",
     "Check how well your True or False statements distinguish student understanding."),
    ("fill", "✏️", "Short responses", "fill_blank",
     "Analyze written responses with support for more than one accepted answer."),
    ("matching", "🔗", "Paired responses", "matching",
     "Evaluate each matching prompt and find the pairs students struggle with."),
    ("written", "📄", "Partial credit", "written",
     "Explore short answers, long answers and essays using awarded scores."),
    ("statistics", "📊", "Whole-test scores", "statistics",
     "Explore your class score distribution, summary statistics and statistical tests."),
]


def render():
    st.markdown(HOME_CSS, unsafe_allow_html=True)
    st.markdown('''
<section class="ia-home-hero" aria-label="Choose your assessment analysis">
    <div class="ia-home-eyebrow">ASSESSMENT INSIGHTS</div>
    <h1>Better questions.<br><span>Clearer understanding.</span></h1>
    <p>Your results have a story to tell. Choose an item type below to discover
    what students understand and where your assessment can improve.</p>
    <div class="ia-home-steps"><span>01 &nbsp; Choose your item type</span>
    <span>02 &nbsp; Upload your results</span><span>03 &nbsp; Explore the analysis</span></div>
</section>
''', unsafe_allow_html=True)
    st.markdown(f'<h2 class="ia-home-heading">{escape(t("sec_choose"))}</h2>'
                '<p class="ia-home-hint">Pick a card to get started. Your Excel template is waiting inside.</p>',
                unsafe_allow_html=True)
    for start in (0, 3):
        for col, (key, icon, tag, target, description) in zip(st.columns(3), CHOICES[start:start + 3]):
            with col, st.container(key=f"analysis_card_{key}"):
                title = t("sec_dist") if key == "statistics" else t(key)
                st.markdown(f'''<div class="ia-select-card">
<div class="ia-select-top"><span class="ia-select-icon" aria-hidden="true">{icon}</span>
<span class="ia-select-tag">{escape(tag)}</span></div>
<h3>{escape(title)}</h3><p>{escape(description)}</p></div>''', unsafe_allow_html=True)
                label = "Explore scores →" if key == "statistics" else f"Analyze {title} →"
                if st.button(label, key=f"choose_{key}", width="stretch"):
                    go(target)
    st.caption(t("privacy"))
