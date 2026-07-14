"""Self-check for lensme.__main__ helpers - runnable directly."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from lensme.__main__ import _code_graph_source


def test_cbm_engine_ignores_stray_graph_html():
    # real bug: a leftover graph.html from an unrelated graphify run must not
    # silently outrank cbm as the Code Graph source once a project is
    # explicitly built with engine="cbm"
    assert _code_graph_source("cbm", True, True) == "cbm"
    assert _code_graph_source("cbm", True, False) == "none"  # not cbm-indexed either
    assert _code_graph_source("cbm", False, True) == "cbm"


def test_graphify_engine_uses_html_only():
    assert _code_graph_source("graphify", True, True) == "iframe"
    assert _code_graph_source("graphify", False, True) == "none"  # no cbm fallback


def test_unknown_engine_probes_like_before():
    # configs written before the "engine" field existed: best-effort probe
    assert _code_graph_source(None, True, False) == "iframe"
    assert _code_graph_source(None, False, True) == "cbm"
    assert _code_graph_source(None, False, False) == "none"


if __name__ == "__main__":
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for fn in tests:
        fn()
        print(f"ok {fn.__name__}")
    print(f"all {len(tests)} tests passed")
