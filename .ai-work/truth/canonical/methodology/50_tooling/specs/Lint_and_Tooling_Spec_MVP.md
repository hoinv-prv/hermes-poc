# Lint and Tooling Spec for AI Work System MVP
Version: 0.2  
Scope: MVP only

---

# 1. Purpose

This spec defines:
- lint scope
- lint behavior
- severity model
- deterministic tooling responsibilities

This version aligns with **Wiki v1.0 freeze**, including:
- `Wiki Source Meta`
- `Wiki Source Index`
- lexical + semantic lookup support
- projection rule between index and meta

---

# 2. Core lint principles

## 2.1. Lint is guardrail, not reviewer
Lint should:
- detect
- report
- suggest minimal corrective action

Lint should not:
- deeply judge semantic truth
- rewrite official content
- replace human review

## 2.2. Deterministic-first support
Prefer:
- metadata checks
- section checks
- enum checks
- path checks
- projection consistency checks
- JSONL/Markdown parse checks

---

# 3. Lint target matrix

## 3.1. AIP
Check:
- metadata valid
- required sections
- step structure
- guideline/skill refs

## 3.2. Active Step Context
Check:
- source AIP exists
- step id exists
- required sections present
- linked pointers well-formed

## 3.3. Workspace
Check:
- required files
- queue/capture parse
- final output presence when done

## 3.4. Queue
Check:
- required fields
- enums
- duplicate ids
- question/why present

## 3.5. Capture Inbox
Check:
- required fields
- enums
- source refs recommended when promote-like targets exist

## 3.6. Official Wiki Entries
Check:
- required metadata
- required sections
- canonical refs
- next reads
- status handling

## 3.7. Wiki Source Meta
Check:
- identity fields
- summary present
- profile mapping present
- artifact reference present
- lookup keys surface present
- relation references well-formed if present
- meta remains within intended structure (not source dump)

## 3.8. Wiki Source Index
Check:
- entry identity fields
- artifact locator present
- meta locator or meta id present
- profile id present
- short summary present
- lookup key projection present
- index entry does not embed full meta
- projection consistency with meta where possible

---

# 4. Severity model

## 4.1. Error
Must fix.

Examples:
- missing required section
- invalid enum
- broken canonical ref
- duplicate queue id
- source meta missing artifact locator
- source index entry missing meta reference

## 4.2. Warning
Should review.

Examples:
- status=needs_review
- source meta missing useful relations
- weak lookup_keys surface
- source index summary too vague
- source meta appears too large/heavy

## 4.3. Info
Helpful but not blocking.

Examples:
- no review hints in non-critical wiki entry
- no optional relation hints
- no optional semantic labels

---

# 5. Default lint profiles

## 5.1. MVP default
- structural lint
- reference lint
- metadata lint
- projection consistency lint (light)

## 5.2. Elevated profile
Allowed only on explicit user request:
- light semantic / consistency lint
- stricter wiki review
- deeper source/meta comparison

---

# 6. AIP lint summary

No major conceptual change from v0.1.

Checks still include:
- metadata
- required sections
- step fields
- guideline/skill refs

---

# 7. Workspace lint summary

No major conceptual change from v0.1.

Checks still include:
- required file presence
- queue/capture parseability
- completion sanity

---

# 8. Official Wiki entry lint

## 8.1. Metadata checks
Required:
- artifact_type
- entry_type
- artifact_id
- title
- knowledge_class
- use_rule
- status
- canonical_references
- last_verified_at
- updated_at

## 8.2. Section checks
Required:
- Purpose
- Scope
- Canonical References
- Recommended Next Reads

## 8.3. Warning checks
- source_of_truth with weak canonical basis
- needs_review entries
- weak next reads

---

# 9. Wiki Source Meta lint

## 9.1. Expected purpose
Meta should remain:
- small
- memory-friendly
- richer than index
- lighter than source artifact

## 9.2. Required metadata / identity
At minimum, source meta should support:
- `source_id`
- `title`
- `source_type`
- `artifact_locator`
- `profile_id`
- `status`

> **`source_type` validation is profile-driven** (CR-AIWS-2026-05-008 / IR-04). A `source_type`
> is valid if it is in the canonical base vocabulary **or** is declared by a shipped profile
> (`wiki_sources/profiles/*.yml` → `source_type:`). To add a project-specific type, declare it on
> a profile rather than hardcoding it in the linter — this keeps the linter in sync with the
> profiles a project actually ships.

## 9.3. Required content areas
Source meta should have at least:
- short summary
- knowledge target hints
- lookup keys
- profile mapping
- artifact pointer/reference

## 9.4. Optional but recommended
- relation hints
- source-specific hints
- change impact hints
- cautions

## 9.5. Warning conditions
- summary too long/heavy
- lookup keys absent or too weak
- relation fields malformed
- meta appears to include large raw source excerpts
- no useful distinction from index

---

# 10. Wiki Source Index lint

## 10.1. Expected purpose
Index is a lookup layer.
It should support:
- scan
- grep/exact lookup
- pointer to meta
- pointer to artifact

## 10.2. Required per-entry fields
At minimum:
- `source_id`
- `title`
- `source_type`
- `artifact_locator`
- `meta_locator` or `meta_id`
- `profile_id`
- `summary_short`
- `knowledge_targets`
- `status`

## 10.3. Required lookup surface
Index entry must contain a reduced lexical lookup surface:
- exact terms / aliases / identifiers / path tokens as appropriate

## 10.4. Critical projection rule
Index entry must **not** embed full meta.

## 10.5. Warning conditions
- no useful lexical keys
- summary too vague to confirm relevance
- index entry too large/heavy
- meta locator broken
- artifact locator broken

---

# 11. Projection consistency lint

Where possible, tooling should check light consistency between:
- source meta
- index projection

## Example checks
- matching source_id
- matching title or equivalent
- matching profile_id
- matching artifact locator
- overlapping lookup key surface

This is not full semantic equivalence checking.
It is just enough to detect obvious drift.

---

# 12. Tooling responsibilities

Tooling in MVP should support:
- building source meta
- building index projection
- looking up source by lexical/exact or simple search
- refreshing source meta
- linting wiki entries, source meta, and index

Tooling should not:
- silently rewrite official wiki
- act as semantic authority

---

# 13. Git-related clarification

Git may be used as an optional change signal during source change detection.

But lint should not require Git metadata in:
- official wiki entries
- wiki source meta
- wiki source index entries

Git is outside the meta contract.

---

# 14. Execution timing recommendations

Recommended lint moments:
- after creating/updating AIP
- after generating Active Step Context
- after creating/updating source meta
- after rebuilding source index
- before finalizing important wiki updates

---

# 15. Conclusion

Lint in MVP now covers:
- official wiki entries
- wiki source metas
- wiki source index

while preserving the frozen design:
- index as projection
- meta as richer source context
- lexical + semantic lookup support
- no silent official rewrite.

---

# 9. Slim Meta/Index Lint Expectations — 2026-05-27 Addendum

**Source:** Applied from wiki_improvement_request.md (validated in vti-ai-work-system-demo, 2026-05-26).

## 9.1 Wiki Source Meta — updated expectations (supplements §3.7)

**Removed sections (lint must NOT flag as missing):**
`## Runtime Use`, `## Source Representation`, `## Change Impact Hints`,
`## Cautions`, `## Profile Mapping`, `## Artifact Reference`.

**Retained required sections:** `## Summary`, `## Knowledge Targets`, `## Lookup Keys`, `## Source-Specific Hints`.

**Blank frontmatter fields:** Lint must NOT flag absence of intentionally-omitted blank fields
(omit-blank pattern). Only flag if a field is present but has an invalid value.

## 9.2 Wiki Source Index — updated expectations (supplements §3.8)

**Fields no longer expected in index entries — do NOT flag as missing:**
- `meta_id` — removed permanently
- `updated_at` — removed permanently
- `knowledge_value` — removed permanently
- `intended_ai_use` — removed permanently

**Acceptable absence:** `original_source_locator` and `representation_locator` absence is acceptable
(omit-when-equal pattern).

**Lint may WARN** if `summary_short` looks like boilerplate:
`"Version: 0.1"`, `"artifact_type: guide"`, `"- (no summary extracted)"`.

---

# 16. Inline `lint_accept` — HUMAN-accepted findings (CR-AIWS-2026-06-065 Addendum)

**Source:** CR-AIWS-2026-06-065 (applied 2026-06-24 via AIP-EXEC-180).

A HUMAN may **accept** (mute) specific lint finding *codes* on a frontmatter-bearing file by adding a `lint_accept` block to that file's own frontmatter. Accepted findings are hidden by default and **excluded from the exit-code counts** — so a reviewed-and-accepted finding (e.g. a deliberately short `Summary` → `meta_summary_degenerate`, or a structural finding on an AIP accepted as-is) no longer keeps `/lint-all` red — while any *other* or *new* finding still surfaces, and the acceptance is **never silent**.

## 16.1 Scope (frontmatter-bearing files only)

`lint_accept` is honored only on files that carry frontmatter and lie under
`.ai-work/wiki_sources/meta/`, `.ai-work/wiki/`, `.ai-work/aip/`, or `truth/AIP_ROOT.md`.

Findings on non-frontmatter targets — workspace directories, JSONL files
(`02_runtime_queue.jsonl`, `08_capture_inbox.jsonl`, `index.jsonl`, `relations.jsonl`,
`maintenance_log.jsonl`), and `.meta.yml` — **cannot** be accepted (there is nowhere to carry
the block); they must be fixed.

## 16.2 Schema (per-code)

```yaml
lint_accept:
  - code: meta_summary_degenerate        # REQUIRED — exact finding code to mute
    reason: "Summary cố ý ngắn, đã review OK"   # REQUIRED — audit trail
    accepted_by: hoinv                    # REQUIRED — who accepted
    date: 2026-06-24                      # optional
```

- **Per-code, never whole-file:** an entry mutes exactly its `code` on that file; other/new findings still surface.
- `code`, `reason`, `accepted_by` are **required** on every entry.

## 16.3 Behavior + exit code

- An accepted finding is moved out of the error/warning counts that drive the exit code: an accepted ERROR no longer returns exit 2; an accepted WARNING no longer returns exit 1 under `--strict`.
- **Never silent:** the text summary shows `accepted=N` (when N>0) plus a hint; `--show-accepted` lists each muted finding with its `reason` + `accepted_by`. JSON output gains a top-level `accepted` array and `counts.accepted`.

## 16.4 Self-guard codes (never acceptable)

- `lint_accept_malformed` (**ERROR**) — an entry missing a required field, not a mapping, or attempting to accept a self-guard code. A malformed block mutes nothing and keeps lint failing.
- `lint_accept_unused` (**WARNING**) — an accept `code` matches no finding on the file (stale/typo'd accept).

Both are emitted by the accept post-pass itself and **cannot** be accepted away.

## 16.5 Reset on refresh (strip-on-refresh; no fingerprint)

A field-preserving rewriter that re-derives a meta's content (`refresh_wiki_source_meta.py`) **strips** the `lint_accept` block on rewrite, so an accept never silently outlives the content it was reviewed against — the HUMAN must re-review and re-accept. There is **no** content fingerprint.

**Known limitation:** strip-on-refresh resets only files that pass through a content-rebuilding rewriter — i.e. **metas**. **AIP files and wiki entries** have no canonical refresh tool, so their accepts reset only when a HUMAN removes the block (a manual edit does not auto-reset). Surgical metadata fixers that do not touch the accepted content's basis (e.g. `normalize_wiki_meta.py`, which only rewrites the `artifact_locator` / `authority_level` lines) intentionally do not strip; a locator fix that resolves the issue instead surfaces as `lint_accept_unused`.

## 16.6 Projection cleanliness

`lint_accept` is a lint directive only — it MUST NOT be projected into the slim Wiki Source Index (it is not in the index's projected field set; the index builder ignores unknown frontmatter keys).

---

# 17. Binary-by-design stub metas — `not_meta_applicable` text-meta exemption (CR-AIWS-2026-06-066)

**Source:** CR-AIWS-2026-06-066 (applied 2026-06-25 via AIP-EXEC-182). Origin: downstream-raised (Otsuka), formalized upstream.

Some source artifacts are **binary by design** — e.g. compiled/binary bodies (ASP `.DP1` DPS binaries, `.FFX` compiled FDG bodies, `.OVD` overlays), PDF object docs, image assets. They have **no text source body**, so a normal text-meta with a Summary / Knowledge Targets / Lookup Keys body and a `profile_id` cannot be derived without fabricating content. The recognized representation for such an artifact is a **stub meta** that carries `not_meta_applicable: true`.

## 17.1 Recognized flag

`not_meta_applicable: true` is a recognized boolean meta-schema flag marking a binary-by-design stub. A descriptive `artifact_kind: binary` MAY accompany it, but the **exemption gates only on `not_meta_applicable is True`** (`artifact_kind` is informational, not a gate).

## 17.2 Lint exemption (scoped)

For a meta with `not_meta_applicable: true`, `lint_wiki` exempts exactly the text-meta requirements such a stub intentionally cannot satisfy:

- **Frontmatter:** `profile_id` is NOT required (scoped carve-out from CR-AIWS-2026-06-004 C1, which otherwise requires `profile_id` on every meta).
- **Body sections:** the required `META_SECTIONS` (Summary / Knowledge Targets / Lookup Keys) are NOT required.
- **Index projection:** the index record's `profile_id` / `summary_short` / `knowledge_targets` are NOT required (kept in sync with the frontmatter exemption).

**Everything else stays required.** The identity fields — `source_id`, `title`, `source_type`, `artifact_locator`, `status` — remain mandatory even for stubs. A *normal* meta (no flag) that omits these sections/fields still errors. The exemption is strictly scoped to the flagged stub.

## 17.3 Index projection

`build_wiki_source_index` projects `not_meta_applicable: true` into the stub's index record **conditionally — only when true**. Because `_omit_blank` keeps `False`, an unconditional projection would bloat every record with `not_meta_applicable: false`; emitting the key only when true keeps normal records lean while letting the index linter apply 17.2.

## 17.4 Regression guard

A golden fixture (`tests/fixtures/wiki_corpus/metas_good/SRC-BINARY-stub-fixture.md`) is guarded by `_lint_golden_fixtures` so `/lint-all` fails if the exemption regresses; a negative fixture (`metas_broken/missing_sections.md`, registered in `test_wiki_regression.py` `sec_lint_negative`) proves a normal meta still errors on missing sections, and `sec_build_index` asserts the stub's record projects the flag.
