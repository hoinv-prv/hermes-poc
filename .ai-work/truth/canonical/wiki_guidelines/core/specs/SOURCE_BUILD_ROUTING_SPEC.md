# SOURCE_BUILD_ROUTING_SPEC (Stage 2 — MVP)

**Status:** active (Stage 1 + Stage 2 MVP, applied 2026-06-15 via AIP-EXEC-101) · **Introduced by:** CR-AIWS-2026-05-019 · **Co-decided with:** CR-AIWS-2026-05-017
**Class:** tooling dispatch (NOT a knowledge-representation layer)

## 1. Purpose

Định nghĩa cách AIWS map một `source_type` → **tool/skill nào dùng để BUILD và REFRESH** wiki source
meta của loại đó. Mục tiêu: source code & artifact đặc thù (Java now; COBOL/Python sau) dùng **bulk
builder chuyên dụng** thay vì luồng generic per-file, mà không phải hardcode trong từng `CLAUDE.local.md`.

## 2. Verified gap (vì sao cần)

- `build_wiki_source_meta.py` (engine) là per-file (1 meta / 1 artifact); `register-wiki-sources` Stage B
  loop per-file cho **mọi** file — **không có nhánh** cho source_type cần bulk builder.
- Đã tồn tại các bulk builder (vd `build_java_wiki_metas.py`, ship trong `tooling/`) nhưng **không có
  chỗ canonical** ghi "source_type X → dùng builder Y" → AI mặc định chạy sai luồng generic trên cây code.

## 3. Config-home invariant (KEY — co-decided với CR-017)

> Đây là quy tắc "per-source_type config sống ở đâu", áp dụng cho CẢ CR-017 lẫn CR-019.

| Mối quan tâm | Sống ở | Ghi/đọc |
|---|---|---|
| **Interpretation + relations** (knowledge_targets, lookup hints, section hints, related_sources) | `profiles/*.yml` + PMP | human/AI-edited (read-mostly) |
| **Build dispatch** (tool nào build/refresh) cần machine auto-upsert | **JSON sidecar riêng** (Stage 2) | machine-written qua tool |

Lý do tách (load-bearing, đã verify): `_common.py dump_frontmatter` chỉ serialize scalar + flat list;
**không có stdlib YAML round-trip writer** → W2 machine-upsert không thể ghi an toàn vào YAML profile.
JSON round-trip sạch bằng `json` stdlib.

Invariant bắt buộc:
- **Cả hai KHÔNG project vào `index.jsonl`** (mirror CR-017).
- `source_type` là **single canonical key** (CR-008 đã làm source_type profile-derived). Build routing
  **không** tạo authoritative key thứ 2; nếu route tham chiếu `profile_id` thì chỉ là **back-reference
  non-authoritative**.
- Build Routing là **tooling dispatch table orthogonal**, KHÔNG phải first-class concept parallel với
  Source Interpretation Profile (tránh lặp shape Knowledge Object đã bị xóa ở CR-005).

## 4. Stage 1 (SUPERSEDED by Stage 2 — retained as history) — static seam, no registry

> Stage 1 routed via a **static table** in `register-wiki-sources` A3b. As of Stage 2 (§5, 2026-06-15) A3b is
> **data-driven** (reads `_build_routing.json`); the static `java_source` row below was migrated into the registry.

Routing was implemented bằng **static table trong skill** `register-wiki-sources` (Stage A3b):

| source_type | bulk builder (reference) | refresh (Stage 1) |
|---|---|---|
| `java_source` | `tooling/build_java_wiki_metas.py --root {root} --source-prefix {prefix} --meta-subdir {subdir}` (preview `--dry-run`) | rerun build trên subdir đã đổi |
| *(project-defined)* | dự án có thể có thêm bulk builder riêng | — |
| *(mọi loại khác)* | **default route** = generic per-file `/build-wiki-source-meta` | `/refresh-wiki-source-meta` |

Quy tắc: **default = generic; bulk = opt-in.** Nếu `source_type` khớp một bulk builder → preview
(`--dry-run`) → chạy → rebuild index + lint, **bỏ qua** loop per-file. Ngược lại → luồng generic.

## 5. Stage 2 (IMPLEMENTED — MVP; CR-AIWS-2026-05-019 Stage 2 applied 2026-06-15 via AIP-EXEC-101)

> **Gate waiver (Approved Deviation, AI_WORK_CONTRACT §5):** Stage 2 was gated on a 2nd real source_type
> (COBOL/Python). The wiki-manager WAIVED that gate on 2026-06-15 to ship the data-driven register command now —
> the MECHANISM is built; **no concrete new source_type route is populated** (registry seeded with `java_source`
> only, migrated from the Stage-1 static table).

Shipped:
- **`_build_routing.json`** (JSON sidecar, `.ai-work/wiki_sources/`, runtime-only) + **`route_build_tool.py`**
  (stdlib CLI: `get/set/list/remove/render`; placeholders `{root}{prefix}{subdir}{artifact}`; `default_route`
  fallback = generic). NOT projected into `index.jsonl` (§3 invariant).
- **Hardening:** portable paths (`__PROJECT_ROOT__` via `portable_locator`/`resolve_locator`); `--args` as a
  shlex string → argv LIST; `render` emits argv list + `shlex.join` preview; tool-path existence re-check at READ
  + soft-WARN at `set`; atomic write (`mkstemp` + `os.replace`); unknown-placeholder WARN. Routing keys are EXACT
  source_types → deterministic (no glob overlap). `lint_wiki` validates the registry (required keys / profile_id
  back-ref / known placeholders / refresh_mode / default_route).
- **Build-tool contract:** a custom builder is stdlib-only, accepts the registry placeholders, supports
  `--dry-run`, and emits a **FULL valid meta** (frontmatter + Summary / Knowledge Targets / Lookup Keys).
  **MVP: there is NO standard `build-wiki-source-meta` completion layer** — the tool's output IS the meta.
  (The two-layer tool-partial → standard-completion model is DEFERRED post-MVP.)
- **W2 — author-on-the-fly + register (directive model):** under ONE explicit HUMAN directive ("build a tool for
  X and register it"), AI authors a builder per the contract, runs it, **format-checks** the output (`lint_wiki`;
  fix-and-rerun if wrong), then registers it — **no second confirm**. AI never authors+registers on its own
  initiative (Rule 8). Wired into `register-wiki-sources` A3b (now data-driven).
- **Refresh = rerun the tool** (`refresh_mode: rerun_tool`); FORBID regenerating a whole directory on a one-file
  change (do-not-clobber).
- **Index always standard** (`build_wiki_source_index.py`); a custom builder never writes the index.

### Revision history
- 2026-06-15 — Stage 2 implemented (MVP) via AIP-EXEC-101 / CR-AIWS-2026-05-019 Stage 2 (gate waived). Stage 1 §4 retained as history; A3b is now data-driven.

## 6. See Also
- `CR-AIWS-2026-05-019` (CR gốc, staged) · `CR-AIWS-2026-05-017` (config-home co-decision)
- `WIKI_META_INDEX_SPEC.md §A12` (deferral — đã amend để sanction spec này)
- IR nguồn: FE/Soumu `AIWS-IR-20260530-wiki-source-build-routing`
