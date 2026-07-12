"""Measure agent exploration tokens: ls/grep/read walk vs one get_context call.

Both strategies answer the same starting question - "where does <task> live,
what is its API surface, and what breaks if I modify it?" - and both end with
the agent reading the primary source file. What differs is everything before
that read:

  baseline: source file listing + grep over the tree + reading the top-3
            candidate files surfaced by grep (blast radius still unknown!)
  lensme:   one get_context(task) call + reading the single read_first file

Usage:
  python examples/bench_context.py <repo_root> <ontology.json> "<task words>"
  python examples/bench_context.py ../fastapi ../fastapi/graphify-out/ontology.json "oauth2 security scopes"

Token counts are the chars/4 heuristic - directional, not tokenizer-exact.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from lensme.mcp import Onto, tool_get_context, _task_words

SKIP_PARTS = {".git", "node_modules", "graphify-out", "__pycache__", ".venv", "dist"}
SOURCE_EXT = {".py", ".ts", ".tsx", ".js", ".jsx", ".go", ".rs", ".java", ".rb"}


def toks(text: str) -> int:
    return len(text) // 4


def source_files(root: Path) -> list[Path]:
    return [
        p for p in root.rglob("*")
        if p.suffix in SOURCE_EXT and not SKIP_PARTS & set(p.parts)
    ]


def main() -> None:
    root, onto_path, task = Path(sys.argv[1]), Path(sys.argv[2]), sys.argv[3]
    words = _task_words(task)
    files = source_files(root)

    # --- baseline walk ---
    listing = "\n".join(str(p.relative_to(root)) for p in files)
    grep_lines: list[str] = []
    hit_files: dict[Path, int] = {}
    for p in files:
        try:
            text = p.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        for i, line in enumerate(text.splitlines(), 1):
            low = line.lower()
            if any(w in low for w in words):
                grep_lines.append(f"{p.relative_to(root)}:{i}:{line.strip()[:120]}")
                hit_files[p] = hit_files.get(p, 0) + 1
    grep_out = "\n".join(grep_lines)
    top3 = sorted(hit_files, key=lambda p: -hit_files[p])[:3]
    top3_reads = sum(toks(p.read_text(encoding="utf-8", errors="ignore")) for p in top3)

    baseline = [
        ("source tree listing", toks(listing)),
        (f"grep for {words} ({len(grep_lines)} hits)", toks(grep_out)),
        (f"read top-3 grep candidates ({', '.join(p.name for p in top3)})", top3_reads),
    ]

    # --- lensme walk ---
    ctx = tool_get_context(Onto(onto_path), {"task": task})
    if "error" in ctx:
        sys.exit(f"get_context: {ctx['error']}")
    primary = root / ctx["read_first"][0]
    primary_toks = toks(primary.read_text(encoding="utf-8", errors="ignore")) if primary.exists() else 0
    lensme = [
        ("get_context(task) reply", ctx["budget"]["estimated_tokens"]),
        (f"read read_first[0] ({Path(ctx['read_first'][0]).name})", primary_toks),
    ]

    b_total = sum(t for _, t in baseline)
    l_total = sum(t for _, t in lensme)
    width = 58
    print(f"\ntask: {task!r}  |  repo: {root.name} ({len(files)} source files)\n")
    print("baseline (ls + grep + read candidates)")
    for label, t in baseline:
        print(f"  {label:<{width}} {t:>8,}")
    print(f"  {'TOTAL':<{width}} {b_total:>8,}\n")
    print("lensme (one get_context call)")
    for label, t in lensme:
        print(f"  {label:<{width}} {t:>8,}")
    print(f"  {'TOTAL':<{width}} {l_total:>8,}\n")
    print(f"exploration tokens: {b_total:,} -> {l_total:,}  "
          f"({100 * (b_total - l_total) / b_total:.0f}% less)")
    print("(baseline still lacks blast radius; get_context includes it)")


if __name__ == "__main__":
    main()
