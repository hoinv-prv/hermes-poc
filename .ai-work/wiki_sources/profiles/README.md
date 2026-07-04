# Wiki Source Profiles (canonical-tooling package templates)

A Source Interpretation Profile tells the meta builders how to interpret a source type (a small
YAML file: `profile_id`, `description`/`source_type`, `knowledge_targets`, optional hints +
`related_sources` scaffold config).

This package ships **only the canonical-tooling profiles the builders depend on** (CR-AIWS-2026-06-047):

- **`java_class.yml`** — required by `build_java_wiki_metas.py` (it emits `profile_id: java_class`).
- **`knowledge_object.yml`** — required for `node_kind=object` metas (`profile_id: knowledge_object`,
  CR-AIWS-2026-06-004 C1; consumed by `lint_wiki.py`).

A project materializes/extends its own runtime profiles under `.ai-work/wiki_sources/profiles/`.

## Install behavior — content-level MERGE, never overwrite (CR-AIWS-2026-06-047)

`wiki_source_profiles` are **project-owned**. On install/update the canonical profiles are **merged**
into `.ai-work/wiki_sources/profiles/`, never `cp -r`-overwritten:

- Project lacks a profile → the canonical profile is added verbatim.
- Project already has it → only the canonical **top-level keys it is missing** are appended; the
  project's existing keys/values/comments (incl. `extra_stopwords`) are left untouched.

The merge is performed by `merge_wiki_source_profiles.py` (shipped in tooling). AIWS's own *content*
profiles (methodology / wiki_guidelines / preset_knowledge) are AIWS-internal and are **not** shipped.

## Step-2 enrich — project-owned, never overwritten (CR-AIWS-2026-06-048)

A language meta builder runs a canonical **Step 1** (facts → lean meta, AIWS-owned) then a
project **Step 2 enrich** (project-owned). The enrich layer consumes Step 1's *facts dict*
(engine-agnostic — same under regex or tree-sitter) and contributes augmentations the builder
folds in: extra lookup keys, concept keys, edges, sections. Two mechanisms (HYBRID):

**(1) Declarative `enrich:` block (PRIMARY)** — added to the PROJECT's profile (e.g. its own
`java_class.yml` under `.ai-work/wiki_sources/profiles/`; merge-preserved on update, never shipped):

```yaml
enrich:
  lookup_key_patterns:        # each is a Python regex applied VERBATIM to the raw source; every
    - '\b[MA]-\d{2}\b'        #   match becomes an extra lookup key. Use SINGLE backslashes and a
                              #   single-quoted scalar (this minimal YAML reader does NOT unescape).
  concept_keywords:           # signal token (annotation / type-name / package) -> concept keys
    Scheduled: ["batch job", "scheduled task"]
```

Single-token added keys still pass the CR-043 code-key stopword filter; multi-word keys are kept.
With no `enrich:` block and no hook, Step-2 contributes nothing → output is byte-identical to Step-1.

**(2) Optional code-hook (ESCAPE)** — for logic beyond declarative rules, the project may add
`.ai-work/wiki_sources/enrich/<source_type>.py` (e.g. `java_source.py`) exposing:

```python
def enrich(facts: dict, src: str, ctx: dict) -> dict:
    """Pure, deterministic. Return any of:
    {extra_lookup_keys: [...], extra_concepts: [...], extra_edges: [...], extra_sections: [...]}."""
    return {}
```

`apply_enrich` imports the hook **if present** (absent → declarative-only; import/run error → logged
and skipped, never breaks Step 1). The hook is **project-owned and never shipped**. `extra_edges`
items may be `{"target","role","basis"}` dicts (or strings); `extra_sections` items are full
markdown blocks appended before `## Cautions`.

## Lookup-key stopwords (CR-AIWS-2026-06-043 Change A)

Lookup-key extraction drops generic noise words so keys stay discriminating. Universal built-in
stopword sets (English function words, common-English filler, web/CSS/JS, Vietnamese/UI-CRUD) live
in `_common.py` and are **never** project config. Two **project-tunable** knobs let a project add
its own generic terms **without editing any builder**:

- **`project_stopwords.yml`** (sibling of the profiles): a project-wide `stopwords:` list applied to
  **all** source types. It is **project-authored** — **not shipped** and **never written** by the
  install (CR-047 Change C). `configured_stopwords()` reads `<profiles dir>/project_stopwords.yml`
  if the project created one.
- **`extra_stopwords:`** (optional field on a profile, e.g. `knowledge_object.yml`): a list scoped
  to **one** source type only. Empty / absent = no effect (parser-tolerant); merge-preserved.

Matching is **case-insensitive, single tokens only** — multi-word curated keys (e.g.
`member management`) are never filtered. **Never ship populated project term-lists upstream** — these
templates stay empty; each project fills its own.

## `emit_scaffold` (CR-AIWS-2026-06-043 Change B)

A profile's `related_sources.emit_scaffold: false` (e.g. `knowledge_object.yml`) is honored as a
real boolean — the builder no longer re-emits an empty `## Related Sources` TODO scaffold for
profiles that opt out. Defaults to `true` when omitted.
