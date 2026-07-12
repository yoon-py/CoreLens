# lensme

C4-style ontology layer on top of [graphify](https://github.com/Graphify-Labs/graphify)'s `graph.json`.

![FastAPI mapped by lensme](docs/assets/map-fastapi.png)

*[FastAPI](https://github.com/fastapi/fastapi) (2,718 files) mapped with zero
config: source features first, docs/examples/tests sidelined into supporting
bands, real externals (starlette, pydantic) from `pyproject.toml`.
[Demo GIF](docs/assets/demo-fastapi.gif) shows the detail panel and
change-impact analysis.*

Turns a raw code knowledge graph (thousands of AST nodes) into a navigable,
always-fresh map a human can actually read:

```
Product > Feature > Component > Module > File   (+ External, Database)
```

Interactive UI: banded hierarchy canvas (level = row), per-level cards,
relationship edges, detail panel with metrics and change-impact analysis.

## Quick start

```bash
# 0. once: install (from this repo)
uv tool install --editable ./lensme
(cd lensme/ui && npm install && npm run build)

# 1. build the code graph with graphify (writes graphify-out/graph.json)
graphify .

# 2. build the ontology
lensme build --prefix myproject/ --name myproject

# 3. open the map
lensme serve
```

`lensme serve --watch` keeps the map fresh: when graphify rewrites
`graph.json` (its `--watch` mode or commit hook), the ontology is rebuilt
automatically and the browser picks it up within seconds.

## Commands

| command | what it does |
|---|---|
| `lensme build --prefix p/ --name x [--enrichment e.json] [--tree]` | graph.json → ontology.json; saves config for `sync` |
| `lensme sync` | rebuild using the saved config |
| `lensme sync --watch` | poll graph.json, rebuild ontology on change |
| `lensme serve [--watch] [--port N]` | serve UI + ontology.json (+ graph.html, hotspots.json), open browser |
| `lensme symbols --prefix p/ [--changed]` | per-file symbol digest for agent enrichment (hash-cached) |
| `lensme tree ontology.json` | pretty-print an ontology |
| `lensme mcp [--ontology o.json]` | MCP server (stdio, zero-dep): `get_context` / `overview` / `search` / `component` / `impact` tools for agents |
| `lensme impact-check [--repo r] [--files ...]` | blast radius of staged files - informational, never blocks; `--install-hook` writes a pre-commit hook |
| `lensme hotspots [--repo r] [--since "6 months ago"]` | git churn + co-change joined onto the ontology; flags co-changed pairs with **no** structural edge (hidden coupling); feeds the UI heatmap |
| `lensme diff old.json new.json [--json]` | structural diff: components/files added/removed, relationship count deltas, blast-radius changes - the engine for PR architecture reports |

## Git integration

```bash
# pre-commit: see the blast radius before you commit (never blocks)
lensme impact-check --install-hook --repo . --ontology graphify-out/ontology.json

# architecture time machine: churn heatmap + hidden coupling
lensme hotspots --repo . && lensme serve   # then toggle "Show Hotspots"

# PR report core: diff two builds
lensme diff main-ontology.json feature-ontology.json
```

## Design

Two stages, mirroring graphify's own extraction philosophy:

1. **Deterministic skeleton** - no API key, no LLM. Directory nesting, path-token
   domain discovery, package-manifest externals, import-statement scanning.
   Works well for domain-nested codebases (`src/components/billing/...`).
2. **Agent enrichment (optional)** - for flat packages where directories carry no
   signal, a host agent (e.g. Claude running this tool) classifies files into
   components from their symbol digests. See `docs/enrichment-spec.md`.
   No separate API key needed when run inside an agent session.

Every node carries an honest confidence tag - surfaced in the UI's
Properties tab:

- `EXTRACTED` - structural fact from the graph (files, imports, calls)
- `INFERRED-heuristic` - path/naming rule
- `INFERRED-llm` - agent classification (with rationale)

## Output schema (`ontology.json`, schema_version 2)

```jsonc
{
  "schema_version": 2,
  "meta": { "built_at", "source_graph", "graph_stats", "level_counts" },
  "type": "Product", "name": "...", "description": "...", "stats": {...},
  "children": [ /* Feature > Component > Module > File, each with
                   confidence, rationale, description, responsibilities, stats;
                   File nodes carry symbols: [{name, line}] */ ],
  "component_relationships": [   // rolled up from file-level graph edges
    { "source", "target", "relation": "depends_on|calls|references|implements|integrates_with",
      "confidence": "EXTRACTED", "count": 3 } ],
  "file_relationships": [...],   // v2: the same edges before component rollup
  "external": [...],             // from package manifests
  "database": [...],             // keyword-detected data stores
  "impact": { "<component_id>": { "direct": [...], "indirect": [...], "total_files": N } }
}
```

## Agent token savings

`get_context` gives a coding agent its starting context in one MCP call -
the owning component, files ranked by task relevance with their symbols,
read-first suggestions, dependencies, and blast radius, trimmed to a token
budget. Source components always outrank docs/tests bands.

Measured on FastAPI for the task "oauth2 security scopes"
(`python examples/bench_context.py <repo> <ontology.json> "<task>"`):

| exploration strategy | tokens |
|---|---|
| ls + grep (905 hits) + read top-3 grep candidates | 48,961 |
| one `get_context` call + read the suggested file | 8,008 |

**84% fewer exploration tokens**, and the baseline walk still doesn't know the
blast radius (1,165 files) that `get_context` includes. The ontology saves the
*search* tokens, not the final read: it tells the agent which 1 file to read
instead of which 30 to sift.

## Validated against external repos

Run on [FastAPI](https://github.com/fastapi/fastapi) (2,718 files, ~74% of
which are docs/translations - a worst case for path heuristics):

- `tests/`, `docs/`, `docs_src/` are classified as supporting bands and sorted
  after the product source instead of drowning it (before this, "Docs" was the
  top feature with 2,016 files).
- Externals are read from `pyproject.toml` / `requirements.txt`, not just
  `package.json`: starlette, pydantic, typing-extensions detected with
  `integrates_with` edge counts per component.
- Flat packages (no directory signal) set `meta.enrichment_recommended` and the
  CLI prints a hint, instead of inventing features from filename tokens.

The FastAPI failure modes are pinned as regression tests in
`tests/test_build.py` (`test_support_kinds_sidelined`,
`test_python_manifest_externals`, `test_flat_package_flag`).

## Development

```bash
python tests/test_build.py        # pipeline self-check (no deps)
python tests/test_insights.py     # impact-check / hotspots / diff self-check
cd ui && npm run dev              # UI dev server (proxies /ontology.json to :4173)
cd ui && npm run build            # typecheck + production build
```
