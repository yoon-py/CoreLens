"""Self-check for lensme.mcp tools - runnable directly: python tests/test_mcp.py"""
import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from lensme.build import build_ontology
from lensme.mcp import Onto, tool_get_context, tool_search
from tests.test_build import _graph


def _onto(tmp: Path) -> Onto:
    onto = build_ontology(_graph(), prefix="proj/", product_name="proj")
    p = tmp / "ontology.json"
    p.write_text(json.dumps(onto), encoding="utf-8")
    return Onto(p)


def test_get_context_by_task():
    with tempfile.TemporaryDirectory() as td:
        o = _onto(Path(td))
        out = tool_get_context(o, {"task": "fix the billing invoice rendering"})
        assert "error" not in out, out
        assert "billing" in out["component"]["id"], out["component"]
        # the invoice file must rank first (path + symbol hits)
        assert "Invoice.tsx" in out["read_first"][0], out["read_first"]
        assert out["budget"]["estimated_tokens"] <= 2000


def test_get_context_budget_trim():
    with tempfile.TemporaryDirectory() as td:
        o = _onto(Path(td))
        big = tool_get_context(o, {"task": "billing invoice"})
        small = tool_get_context(o, {"task": "billing invoice", "budget": 60})
        assert small["budget"]["estimated_tokens"] < big["budget"]["estimated_tokens"]
        # symbols are shed before files; at least 3 files always survive
        assert len(small["files"]) >= min(3, len(big["files"]))


def test_get_context_no_match():
    with tempfile.TemporaryDirectory() as td:
        o = _onto(Path(td))
        assert "error" in tool_get_context(o, {"task": "quantum flux capacitor"})
        assert "error" in tool_get_context(o, {})


def test_get_context_by_component():
    with tempfile.TemporaryDirectory() as td:
        o = _onto(Path(td))
        out = tool_get_context(o, {"component": "component_billing_store"})
        assert out["component"]["id"] == "component_billing_store"
        assert out["dependents"], "billing store has an incoming depends_on edge"


def test_search_still_works():
    with tempfile.TemporaryDirectory() as td:
        o = _onto(Path(td))
        hits = tool_search(o, {"query": "renderInvoice"})
        assert hits["total"] >= 1


if __name__ == "__main__":
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for fn in tests:
        fn()
        print(f"ok {fn.__name__}")
    print(f"all {len(tests)} tests passed")
