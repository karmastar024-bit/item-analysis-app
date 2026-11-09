"""Every page must load with no exception (no upload needed)."""
from pathlib import Path
import pytest
from streamlit.testing.v1 import AppTest

ROOT = Path(__file__).resolve().parent.parent

def _call(mod, fn):
    import importlib
    getattr(importlib.import_module(mod), fn)()

PAGES = [("pages.true_false","render"),("pages.fill_blank","render"),("pages.matching","render"),
         ("pages.written_response","render"),("pages.score_statistics","render"),("pages.home","render")] + \
        [("pages.guides",f) for f in ("about","how_it_works","item_guide","decision_rules",
         "statistical_tests_guide","methodology","data_format","sample_data","contact","feedback")]

@pytest.mark.parametrize("mod,fn", PAGES)
def test_page_loads(mod, fn):
    at = AppTest.from_function(_call, args=(mod, fn), default_timeout=60).run()
    assert not at.exception, at.exception

def test_entry_point_and_navigation():
    at = AppTest.from_file(str(ROOT / "app.py"), default_timeout=90).run()
    assert not at.exception, at.exception
    assert [b.label for b in at.button][:5] == ["📝\n\nMCQ","✔️\n\nTrue or False","✏️\n\nFill in the Blanks",
                                                 "🔗\n\nMatching","📄\n\nLong / Essay"]
    assert "ITEM ANALYZER" in " ".join(m.value for m in at.markdown)

def test_legacy_mcq_page_loads():
    at = AppTest.from_file(str(ROOT / "pages" / "mcq.py"), default_timeout=90).run()
    assert not at.exception, at.exception
