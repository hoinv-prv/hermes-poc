---
name: lookup-wiki-source
description: Lookup source candidates through the Wiki Source Index; then read the chosen meta via the wiki_meta value-add reader (tooling, not the whole file) and use wiki_relations for impact/reverse
user-invocable: true
---

# SKILL: lookup-wiki-source

## Purpose
Fast, grep-friendly lookup of source artifacts via the Wiki Source Index.
Use this before opening raw artifacts so you pick the right source first.

## Tool
`.ai-work/tooling/lookup_wiki_source.py`

### Examples
```
# lexical search (default)
python .ai-work/tooling/lookup_wiki_source.py --query "manufacturing order"

# exact id
python .ai-work/tooling/lookup_wiki_source.py --query SRC-FUNC-MO-UPDATE --mode id

# path-token match
python .ai-work/tooling/lookup_wiki_source.py --query "inventory/update" --mode path

# default output is slim (1 line/result, routing fields only) — keep recall high, low cost
python .ai-work/tooling/lookup_wiki_source.py --query "booking" --limit 20

# verbose: full multi-line records (summary / authority / representation inline) — for content verification
python .ai-work/tooling/lookup_wiki_source.py --query "booking" --limit 5 --full

# continue past a truncated result set (skip already-checked ids)
python .ai-work/tooling/lookup_wiki_source.py --query "booking" --excludes "SRC-A,SRC-B"
```

## Scope & raw search (CR-AIWS-2026-06-052)

- **Default scope = `project,aiws`** (registered project + AIWS indices). A bare `--query` searches exactly those. `local` is rule-#11-gated — opt-in only via `--scope project,local --authorized human` (after a HUMAN authorizes local-wiki search). `--scope all` = `project,local,aiws` (also needs `--authorized`).
- **Raw (un-registered) search is authorization-gated + never silent.** `--include-raw {off|on-empty|always}` (default `off`) Globs/greps the project dirs listed in `document_search_guidelines.md`; it **REQUIRES** `--authorized {human|aip|agent-rule}`. The `on-empty` fallback fires only for an **object** lookup (`--lookup-mode object`) that returns 0 registered hits. Absent `--authorized` (any raw, or scope beyond `project,aiws`) → the tool **refuses (rc≠0)**: STOP and ask HUMAN. Raw hits are labelled `unregistered:` and ranked below registered results.
- Multi-system (rule #12) is orthogonal and not waived by a raw/AIP grant — `multi_system:true` still hard-requires `--system`/`--all-systems`.

## Search orchestration — match need → tool

| Need | Shape | Tool |
|---|---|---|
| A doc/concept (no id yet) | FIND | `lookup --query X` |
| All nodes of a kind (every function / table) | ENUMERATE | `lookup --query <broad> --source-type function\|table` |
| What a node relates to / who depends on it | TRAVERSE | `wiki_relations --relations <id>` |

**Chain rule:** `wiki_relations` needs a `source_id` (an output of `lookup`) — FIND/ENUMERATE first, or `lookup --mode id` (`SRC-FUNC-Fxx`, `SRC-TABLE-<NAME>`). **Pick edges by need:** `x:reads`/`x:writes` = function↔table; `x:calls` = function→function; `x:part_of` = table FK; `represents`/`companion_requirement` = the RD/BD/FUNC set of one function; `system_foundation` = OVERALL/CRUD baseline.
❌ Don't `Read` the whole `index.jsonl`/`relations.jsonl` to enumerate — use `--source-type` / `wiki_relations` / grep (≈2× cheaper).

## Flow
1. Form a short query using a concept / identifier / path fragment.
2. Run the tool. It returns ranked entries with pointers to meta + artifact.
3. **Read the meta via the value-add reader** — `python .ai-work/tooling/wiki_meta.py --view <source_id>` — NOT by
   opening the whole meta file. It prints the orientation value-add (Summary / Source-Specific Hints / Cautions /
   a Related Sources **signal** — out-edge count+types, NOT the full edges) and SKIPS what you already saw at lookup
   (Lookup Keys / Knowledge Targets). The Related Sources signal is **out-only** — for the full out+in (reverse /
   impact) picture run `wiki_relations.py --relations` (step 4); don't treat the signal as "all relations". Don't
   re-read discovery fields.
4. **Impact / reverse (opt-in, one-hop):** if the task needs "who points AT / who calls X / what feeds this", run
   `python .ai-work/tooling/wiki_relations.py --relations <source_id>` (out-edges + IN-edges).
   - **Mapping relationships/coverage (not finding one route):** the edge set IS the deliverable — put EVERY
     declared `x:`-edge into the answer and *justify* any exclusion inline; don't silently drop a seen edge as
     "out of scope". A seen-then-dropped edge is a recurring under-recall — distinct from a missing-edge coverage
     gap (fix the latter in the meta's Related Sources, not here).
5. Open the `artifact_locator` only if the meta is not enough — and use the meta's **Source-Specific Hints** to open
   the RIGHT section, not the whole file.
   - **Mapping/coverage/impact tasks — recover undeclared references:** after reading the artifact, for each
     reference it names in its **body** that is NOT a declared `## Related Sources` edge (a doc it cites but doesn't
     link — e.g. message-list / code-master-definition docs), run a separate `lookup --query <ref> --limit 5`.
     `wiki_relations` only returns declared edges, so these never surface via TRAVERSE — skipping them silently
     drops needed docs. (Mapping/coverage/impact only — not single-route FIND.)

## Choosing `--limit` / `--slim` (intent-aware)

Slim output is the **default** (1 line/result: score, source_id, title, source_type, meta_locator)
— it keeps recall high at low cost (~−81% text / −93% json vs verbose). The cost driver is
**fields-per-result**, not result count: don't shrink `--limit` to save tokens (you drop
foundational / downstream docs). Pass **`--full`** only when you need the inline summary /
authority / representation fields (e.g. a content-verification read).

| Intent | `--limit` | How to query |
|---|---|---|
| Targeted (you know the doc) | 3–5 | Lead with a distinctive token (F-code, doc id) or `--mode id` |
| Intermediate (know topic, not boundary) | 8–10 | Tier-2 / downstream docs rank ~9–15, so 5 is too narrow |
| Exploratory (unsure what you need) | 15–20 | Slim default keeps recall high; widen the limit, don't add fields |

**Score-gap heuristic:** a clear gap (e.g. 27 / 23 → 12) = confident hit, stop. A flat / floor
distribution (many low scores) = widen the limit or sharpen the query.
If the tool prints "… N more match(es) not shown", `--limit` clipped the set (`has_more`) — recall
isn't exhausted. When current hits look insufficient, you **may** re-run with
`--excludes <ids already checked>` to page the next batch (or raise `--limit`). Continuing is your
reasoning call — don't crawl the whole index by default.
An AIP step or HUMAN may override `--limit` / `--mode` / `--full` per use-case.

## Routing, not verification

A lookup result is a **candidate route**, not evidence. The index/meta is an identification
layer, not a content copy — errors that live in the document body (broken cross-refs, internal
contradictions, traceability gaps, version-skew) are invisible to lookup alone. When **authoring
or reviewing** (not merely locating), full-read the Tier-1 docs the work traces to and run:

```
□ Every cited filename/§ resolves to a real file/section?
□ Any internal or RD↔BD contradiction (e.g. VAL IDs misnumbered)?
□ Every VAL traces to a BR/FR? Tables referenced in §9 exist in the data model?
□ Field names consistent API↔DB? Any leftover TBD / version-skew?
```

Confidence gate: candidates at the score floor (low overlap) → meta-only, log a
"low-confidence skip"; do not full-read them.

## No-match escalation (MANDATORY)

When the tool returns `(no matches)` (exit code 1), **do not stop**. The index
may be incomplete — the source may exist as a raw artifact not yet registered.

```
Step 1 — Retry semantic mode (if first attempt was lexical):
  py .ai-work/tooling/lookup_wiki_source.py --query <keyword> --mode semantic

Step 2 — Raw search:
  a. Open .ai-work/wiki/reference/document_search_guidelines.md
     → section "Raw search fallback — project artifact directories"
     → lists artifact dirs for this project
  b. Glob **/*.md in those dirs, filter by filename
  c. Grep <keyword> in artifact dirs if filename search is insufficient

Step 3 — If no artifact dirs documented in guidelines:
  → Ask HUMAN: "Index miss for '<keyword>'. Which directories hold raw artifacts?"
  → After answer: update document_search_guidelines.md with the info

Step 4 — If found in raw:
  a. Read the artifact directly for this task
  b. Register it later: /build-wiki-source-meta

Step 5 — Only report "no relevant documents" if steps 1–4 all miss.
```

❌ **Never silently conclude "not found" after a single index miss.**

## Rules
- **Multi-system (CR-AIWS-2026-06-017):** in a `multi_system: true` project, `lookup_wiki_source.py` ERRORS (rc≠0) if `--system <id>`/`--all-systems` is missing. On that error, **STOP and ASK the HUMAN** for the active system — never ignore it, never auto-set/guess a system; carry the chosen `--system` through the task. Never merge specs across systems.
- do not bypass the index by grepping the whole repo first (index-first)
- confirm relevance via meta before opening the artifact
- index miss → escalate per no-match protocol above; never silently give up
- **Object nodes** (`node_kind=object`, `__OBJECT__`) live in the SAME index and are found by the SAME lookup — no `--kind` flag (DP7). "Everything about X / who calls X" = `wiki_relations.py --relations <source_id>` (out+IN edges), NOT lookup.
