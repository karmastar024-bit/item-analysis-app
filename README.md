# ITEM ANALYZER
**Made for Educators in Bhutan** — item analysis for MCQ, True/False, Fill-in-the-Blank, Matching and written items,
plus test-distribution statistics (t-tests and z-tests).

Author: **Karma Dorji** · karmastar024@gmail.com

## Features
- Dashboard explaining Difficulty (p), Discrimination (D) and Distractor Efficiency (DE), with formulas and worked examples
- Decision rules per item type; every decision shows the **exact reason** (e.g. *REVIEW – Difficulty is high (p = 0.87).*)
- Upload validation with friendly messages (no tracebacks), sample data for every type
- Test distribution: descriptive statistics, histogram, box plot, one-sample / independent / paired t-tests, one- and two-sample z-tests
- Downloads: CSV, Excel, PDF (item reports); CSV (test results)
- Language selector (English, Dzongkha starter set) built on a translation dictionary
- Privacy: files are processed in memory only; nothing is stored or sent anywhere

## Supported item types
| Type | Category | Statistics |
|---|---|---|
| MCQ | Selected-response | p, D, **DE** |
| True or False | Selected-response | p, D (DE not applicable) |
| Matching | Selected-response | p, D (each prompt = 1 item) |
| Fill in the Blanks | Short constructed-response | p, D |
| Short / Long Answer, Essay | Written constructed-response | normalized p, score-based D |

## Statistical methods
- **p** = correct ÷ students (binary) · **p** = mean score ÷ max score (written, *normalized difficulty*)
- **D** = (U − L) ÷ g with top/bottom 27% groups (binary) · (mean_upper − mean_lower) ÷ max (written)
- **DE** = functional distractors ÷ distractors × 100 (functional = chosen by ≥ 5% of students), MCQ only
- **Decision:** DISCARD if D<0, p=0, p=1 (or DE=0% for MCQ) → REVISE if D<0.20 and p∉[0.20,0.80] → REVIEW if either → RETAIN
- Tests: one-sample t, independent t (Welch default, pooled optional), paired t, one-sample z, two-sample z (σ known)

Full formulas are on the in-app **Methodology** page.

## Installation
```bash
git clone https://github.com/karmastar024-bit/item-analysis-app.git && cd item-analysis-app
pip install -r requirements.txt
streamlit run app.py
```
Tests: `python -m pytest tests -q`

## Streamlit Community Cloud
Main file path: `app.py` · Python 3.10+ · dependencies from `requirements.txt`.

## Data format
One row per student, first column `StudentID` (use IDs, not names).
- **MCQ:** the two Excel templates in `templates/` (answer key + student responses)
- **True/False, Fill, Matching:** a row with `StudentID = KEY` holds the answer key (Fill: alternatives separated by `|`)
- **Written:** a row with `StudentID = MAX` holds each item's maximum score; cells hold scores awarded

## Sample data
`data/` — `sample_mcq_*.xlsx`, `sample_true_false.csv`, `sample_fill_blank.csv`, `sample_matching.csv`, `sample_written.csv`
(regenerate with `python -m utils.make_samples`). They contain deliberately flawed items.

## Project structure
```
app.py            router, header, footer          item_analyzer.py   original MCQ engine (kept)
pages/            home, mcq (original UI), true_false, fill_blank, matching,
                  written_response, score_statistics, guides, binary_common
analysis/         difficulty, discrimination, distractor, decision, scoring,
                  binary_analysis, written_analysis, statistical_tests
components/       navigation, footer, charts, tables, explanations
utils/            data_validation, file_handlers, translations, make_samples
```
`pages/score_statistics.py` is deliberately **not** named `statistics.py`: that would shadow Python's standard-library module.

## Known limitations
- Dzongkha covers only a few interface strings; long explanations are English (missing keys fall back to English). Needs native-speaker review.
- MCQ keeps its original two-file Excel workflow and visual style; other types use a single-file layout.
- Item statistics are unstable below ~30 students (the app warns).
- PDF reports cover item-analysis results and summary charts; test-distribution results are CSV only.
- Matching has no partial credit within a prompt.
- Not yet tested in a real browser with a long-lived session (automated tests use Streamlit's headless harness).

## Future development
More languages (Spanish, French, Hindi), full Dzongkha, MCQ single-file upload, reliability (KR-20 / Cronbach's α), non-parametric tests, PDF for statistics.
