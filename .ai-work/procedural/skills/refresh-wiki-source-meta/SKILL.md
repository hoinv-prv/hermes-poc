---
name: refresh-wiki-source-meta
description: Refresh a Wiki Source Meta against its source artifact (preserve resolved ## Related Sources, drop legacy ## Profile Mapping) and detect material change; rebuild relations.jsonl after
user-invocable: true
---

# SKILL: refresh-wiki-source-meta

## Purpose
Re-project a Wiki Source Meta when the underlying source artifact may have
changed. Reports whether material change was detected (lookup keys, summary,
knowledge targets) so you can decide whether the wiki needs an update.

## Design notes (CR-022/024/025)
- **Preserve the RESOLVED `## Related Sources`** on refresh — never clobber human/AI-resolved edges (only re-emit the
  scaffold if it was never resolved). Legacy `## Profile Mapping` is dropped (mirrored frontmatter). Keep/resolve basis
  notes per the objective-stakes, intent-blind convention (build-meta SKILL / `Knowledge_Expansion_Link_Spec_MVP.md` §4.4).
- **Merge curated `## Lookup Keys` (union)** on refresh (CR-AIWS-2026-06-012 Fix 6) — the builder re-derives lookup keys mechanically, so refresh UNIONs curated+new (curated first, case-insensitive de-dup) and **never drops a curated key**; pass `--regenerate-lookup-keys` to re-derive from scratch instead.
- **After a refresh that changes `## Related Sources` → rebuild** `python .ai-work/tooling/build_relations.py`.
- Read a meta via `python .ai-work/tooling/wiki_meta.py --view <id>` (value-add reader), not the whole file.
- **Sourceless refresh (node_kind=object):** an object meta has `artifact_locator: __OBJECT__` (no backing file) → `refresh_wiki_source_meta.py` source re-read does NOT apply and `detect_changed_wiki_sources.py` won't flag it (no mtime). Refresh BY HAND: re-validate identity (`source_id` frozen), `## Summary`, and `## Related Sources`; set `updated_at` = `now_utc_iso()` (write time); then `build_relations.py`. (Source-backed refresh auto-stamps `updated_at` = source file mtime via re-projection — CR-AIWS-2026-06-024.)

## Tools
- `.ai-work/tooling/detect_changed_wiki_sources.py` (optional)
- `.ai-work/tooling/refresh_wiki_source_meta.py`
- `.ai-work/tooling/evaluate_wiki_source_impact.py` (optional)

### Example
```
# Detect first
python .ai-work/tooling/detect_changed_wiki_sources.py

# Refresh one meta (writes a draft by default)
python .ai-work/tooling/refresh_wiki_source_meta.py \
  --meta .ai-work/wiki_sources/meta/SRC-DESIGN-001.md \
  --profile .ai-work/wiki_sources/profiles/design_doc.yml

# Apply in-place (with backup)
python .ai-work/tooling/refresh_wiki_source_meta.py \
  --meta .ai-work/wiki_sources/meta/SRC-DESIGN-001.md \
  --profile .ai-work/wiki_sources/profiles/design_doc.yml \
  --apply

# Then rebuild the index
python .ai-work/tooling/build_wiki_source_index.py
```

### Flags
- `--apply` — overwrite in place (default writes a `.refresh.md` draft).
- `--regenerate-summary` — re-derive Summary instead of preserving the curated one (default preserves; Fix 1).
- `--regenerate-lookup-keys` — re-derive Lookup Keys instead of union-merging the curated ones (default merges; Fix 6, CR-AIWS-2026-06-012).
- `--review-decision <d>` — traceability of the review outcome; use `approved_to_apply` when applying after review (drives `maintenance_status`/`review_status`).
- `--impact-level <l>` / `--change-summary <s>` — recorded in the maintenance log.

## Flow
1. Detect candidates (`detect_changed_wiki_sources.py`).
2. For each candidate, refresh without `--apply` and diff the draft.
3. If material change: optionally `evaluate_wiki_source_impact.py` to see
   which wiki entries may need review; open a wiki candidate update task
   (`AIP_EXEC`) to drive the actual wiki changes — tooling must not
   rewrite wiki entries silently.
4. Apply refresh and rebuild the index.
5. **Object/relation re-check:** nếu refresh cho thấy artifact nay mô tả object MỚI, hoặc lộ quan hệ object↔object (domain) / object↔artifact (representation) MỚI/đổi chưa khai trên object node → append candidate `object_relation_capture` + đề xuất HUMAN cập nhật object node (`x:`/`represented_by` edges, khai một lần — ghi đủ MỌI edge mới, đừng dừng ở cạnh đầu). Suggest-only (rule #7/DP6/INV-8); domain edges đã resolved trên object node được PRESERVE (refresh không tự derive/ghi đè). **Khi re-check lộ object MỚI hoặc edge MỚI/đổi → PRESENT hai bảng (Detected Objects / Discovered Relations, chỉ các dòng mới/đổi) cho HUMAN confirm, đồng thời append candidate** (suggest-only; edge đã resolved giữ nguyên). Chi tiết: `capture_triggers/object_relation_capture.md`.

## Rules
- never let tooling rewrite official wiki entries
- material change is a signal, not an approval
- always go through a wiki candidate / review before applying wiki updates

---

## CR-S6: Promotion Gate (2026-05-25)

Source: AIP-EXEC-015 STEP-04, CR-S6.

### Change type detection

Before applying any meta refresh, classify the change type:

**Lightweight (proceed normally):**
- Fix typo in lookup key, summary, caution
- Add new lookup key (not removing existing T1)
- Update `task_relevant_tags`
- Fix `representation_locator` or `updated_at`
- Minor Summary rewrite (scope unchanged)

**Promotion trigger (HARD STOP):**
Ref: `Controlled_Knowledge_Promotion_Spec_MVP.md §CR-D8 Addendum`:
1. Set `knowledge_class: source_of_truth`
2. Change `source_id` of a referenced meta
3. Split or merge meta records
4. Mark important artifact `deprecated`
5. Re-type/remove a `## Related Sources` edge that other metas depend on (run `wiki_relations.py --relations <source_id>` for IN-edges first)

### Gate behavior

```
IF change_type = Promotion trigger:
  → HARD STOP
  → Inform user: "This change requires Controlled Promotion (CR + wiki manager)"
  → Write log entry to .ai-work/wiki_sources/_promotion_log.jsonl
  → DO NOT apply refresh
  → Suggest: "Create a CR and submit to wiki manager for approval"

IF change_type = Lightweight:
  → Continue with draft → review → apply flow (unchanged)
```

### Promotion log entry schema

```json
{
  "log_id": "PROM-YYYYMMDD-NNN",
  "artifact_id": "SRC-<id>",
  "trigger_type": "<one of 5 triggers from CR-D8>",
  "change_description": "<what was attempted>",
  "operator": "AI|human",
  "status": "blocked_pending_cr",
  "detected_at": "YYYY-MM-DDTHH:MM:SS"
}
```

Log file: `.ai-work/wiki_sources/_promotion_log.jsonl`

## Traceability
- Step 5 (Object/relation re-check) ↔ governance rule #19. (Code moved out of action text per SKILL_AUTHORING_CONVENTIONS §1 / CR-032.)
