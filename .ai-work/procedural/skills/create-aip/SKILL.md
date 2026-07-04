---
name: create-aip
description: Create an AIP aligned with AI Work System MVP
user-invocable: true
---

# SKILL: create-aip

## Purpose
Create an AIP aligned with:
- SOP-first
- AI Work Contract
- AIP_ROOT / PLAN / EXEC / LOCAL
- Active Step Context
- Workspace-based execution
- Wiki-first knowledge usage

## Inputs
- task/request
- truth/SOP_MASTER.md
- truth/AI_WORK_CONTRACT.md
- truth/AIP_ROOT.md
- relevant truth/wiki refs if available

## PRE-FLIGHT GATE — Artifact Lookup (HARD GATE)

⛔ **HARD GATE — phải thực hiện trước khi mở bất kỳ canonical artifact nào làm input.**

Với MỌI RD/BD/DD/spec dùng làm input, bắt buộc theo đúng trình tự sau:

1. **Lookup trước** — chạy `py .ai-work/tooling/lookup_wiki_source.py --query "<keyword>"` cho từng artifact
2. **Lấy path từ meta** — đọc kết quả, lấy `artifact:` path → mở file
3. **Index miss → escalate** — retry `--mode semantic`; chỉ fallback Glob/Grep sau khi cả 2 miss, và ghi rõ đã escalate

❌ **FORBIDDEN patterns — không có ngoại lệ:**
- Glob/Grep trực tiếp cho artifact file mà không qua wiki lookup trước
- Suy luận path từ artifact khác user đã cung cấp (vd: user cho path DD → tự Glob BD/RD cùng thư mục)
- Bỏ qua lookup với lý do "đã biết chỗ rồi" hoặc "user đã cho path rồi"

✅ **Kể cả khi** user cung cấp path một artifact trực tiếp → tất cả artifact input khác (BD/RD/IT/spec...) vẫn phải qua wiki lookup riêng.

## Outputs
- chosen AIP type
- clarified understanding draft
- drafted AIP content
- unresolved questions if any

## Flow

**[STEP 0a — ALLOCATE AIP ID — MANDATORY, làm TRƯỚC khi draft]** (CR-015 **v2**)
1. Precheck `.ai-work/account_info.yaml` tồn tại (`account_id` + counter). Thiếu → DỪNG, hỏi HUMAN rồi `py .ai-work/tooling/account_id.py set --account-id <id>` (CR-AIWS-2026-06-016); KHÔNG tự bịa `account_id`. (Nghi ngờ file lỗi → `account_id.py validate --repair`.)
2. Lấy id: `py .ai-work/tooling/allocate_aip_id.py --kind exec` (hoặc `plan`/`local`) → ghi vào `artifact_id`.
3. Ghi file AIP mới vào thư mục theo account: `.ai-work/aip/<account_id>/<kind>/AIP-<KIND>-NNN-<slug>.md` (KHÔNG để flat; legacy flat AIPs giữ nguyên).
**KHÔNG tự chọn số bằng glob max+1.** Allocator đọc/ghi per-account counter trong `account_info.yaml`; id format `AIP-<KIND>-NNN` (folder là namespace), gaps khi cancel chấp nhận được.

0. **[WIKI LOOKUP]** Với mỗi input artifact cần đọc (RD/BD/DD/spec):
   - `py .ai-work/tooling/lookup_wiki_source.py --query "<keyword>"`
   - Đọc meta → lấy path artifact → mở file
   - Index miss → escalate (retry `--mode semantic` → raw search theo `document_search_guidelines.md`)
1. Infer task understanding draft
2. Decide if AIP is needed
3. Choose AIP type
4. Ask minimal clarification if needed
4b. **[TASK LENS — front-load inputs]** create-aip resolves inputs up front. Once intent is clear (Intent-first):
   1. **Infer first (primary):** from intent, decide which **subject** docs (RD/BD/DD/spec) and **reference standards** (guideline/checklist/template/SOP) you need — no lens required.
   2. **Lens = additive checklist:** pick a Task Lens or **No-Lens**. If a lens, look it up in `.ai-work/wiki/task_lens_presets/` and use its `relevant_source_types` + `relevant_reference_types` to catch artifacts you missed. It only adds — never bounds/filters.
   3. **Inputs = inference ∪ lens** (never lens-only). Resolve via Flow step 0, fill into `## Required Wiki Inputs` + `## References to Read First`.
      - **Resolving reference standards** (guideline/checklist/template/SOP): query the index by the standard's NAME keywords ("requirement template", "design review checklist"), not the reference_type label; they usually live in `product/wiki_guidelines/`, the AIP templates dir (`TEMPLATE_DIR` — see Step 5), `.ai-work/procedural/`, or carry `source_type` `process_guideline`/`process_template`/`sop` (use `lookup_wiki_source.py --source-type`). Bridge: `*_template→process_template`, `*_guideline/*_checklist/naming_convention/*_playbook→process_guideline`, `sop→sop` (`Task_Lens_Spec` §B). Not findable → Deferred lookup + append a `retrieval_gap` capture.
   4. **Deferred lookups:** for anything unresolved, record `doc + lens` under `## Selected Task Lens / Mode` for run-aip to resolve. No-Lens ⇒ infer fully, skip presets, leave empty. Ref: `Task_Lens_Spec_MVP` §C/§F.
5. **Read template and draft**
   **`TEMPLATE_DIR` (install-portable, CR-AIWS-2026-06-050):** for each template file, read `.ai-work/aip/templates/<file>` if it exists, else `product/aip_templates/<file>` (downstream installs ship only `.ai-work/`; the source repo has both). Template reads below are `TEMPLATE_DIR`-relative.
   **`--template <id|path>` (optional; agent-agnostic):** if the args carry `--template`, instantiate THAT template instead of the default menu. **ID** = case-insensitive basename via alias table (under `TEMPLATE_DIR`): `EXEC→AIP_EXEC_TEMPLATE.md` · `PLAN→AIP_PLAN_TEMPLATE.md` · `LOCAL→AIP_LOCAL_TEMPLATE.md` · `DD_REVIEW`/`DD-REVIEW→AIP_EXEC_DD_REVIEW_TEMPLATE.md` · `BD_REVIEW→AIP_EXEC_BD_REVIEW_TEMPLATE.md` · `APPLY_CR→AIP_EXEC_APPLY_CR_TEMPLATE.md`. **PATH** = a value containing `/` or ending `.md`, resolved from project root. **If the resolved template does not exist → STOP and ASK the HUMAN; NEVER silently fall back to EXEC.** Derive `allocate_aip_id --kind` from it: PLAN→`plan`, LOCAL→`local`, all EXEC variants (incl. DD_REVIEW/BD_REVIEW/APPLY_CR)→`exec`. (create-aip does NOT read `instance.yaml` / agent state — whoever calls supplies `--template`.)
   Before writing a single line of the AIP body:
   - a. Read `<TEMPLATE_DIR>/AIP_EXEC_TEMPLATE.md` (or `AIP_PLAN_TEMPLATE.md` / `AIP_LOCAL_TEMPLATE.md` as appropriate) — also see `<TEMPLATE_DIR>/AIP_EXEC_QUICK_REF.md` for a concise reference
   - a1. **Apply-CR tasks** (applying an already-approved CR): instantiate `<TEMPLATE_DIR>/AIP_EXEC_APPLY_CR_TEMPLATE.md` (lint-conformant condensed EXEC; CR-AIWS-2026-05-037 Option C), not the full EXEC template.
   - b. Note required sections from §6.3 of AIP_Detail_Spec_MVP.md (for EXEC AIPs):
     `## Objective`, `## Execution Scope`, `## Expected Outputs`, `## References to Read First`,
     **`## Execution Steps`** (exact name — NOT `## Steps`), `## Current Risks / Constraints`,
     `## Done Criteria`, `## Self-check / Review Points`, `## Re-plan Rule`, `## Re-plan Log`
   - c. Draft using the template structure directly — do NOT rely on memory of prior AIPs
   - d. Confirm all required sections present before moving to Step 6
6. Draft AIP — **stamp front-matter `template_source: <template-id>`** (write-once provenance = basename of the instantiated template, e.g. `AIP_EXEC_TEMPLATE` / `AIP_EXEC_DD_REVIEW_TEMPLATE`; default menu → `AIP_EXEC_TEMPLATE`). Front-matter ONLY (never a section body), modeled on `runtime_workspace` — do NOT hand-edit. (Consumed by the Agent-Pack run-gate conformance check.)
7. Self-check — **run the checklist below before reporting AIP done**

## Self-check before reporting AIP done (mandatory)

Run through ALL items. Do NOT report "AIP created" until every item passes.

**Format checks:**
- [ ] AIP id obtained via `allocate_aip_id.py` (NOT hand-picked / glob max+1) — see Flow STEP 0a
- [ ] Section `## Execution Steps` present (NOT `## Steps` or any other name)
- [ ] All step headings use exactly: `### Step: STEP-nn — <title>` format
- [ ] Each step has ALL required fields on their own lines (not bold inline):
  `Objective:` / `Recommended Mode:` / `Applicable Guidelines:` /
  `Inputs:` / `Expected Outputs:` / `Done Condition:` / `Notes / Constraints:`
- [ ] STEP numbering is sequential — no gaps (STEP-01, STEP-02, STEP-03…)
- [ ] All required sections per §6.3 present (see Step 5b list above)
- [ ] Front-matter carries `template_source: <template-id>` (write-once basename; default → `AIP_EXEC_TEMPLATE`) — stamped every run; front-matter only (CR-AIWS-2026-06-050)

**Content checks:**
- [ ] Governance Note accurately reflects scope — especially for mixed-governance AIPs (see Rules below)
- [ ] Done Criteria reference Gate compliance when applicable
- [ ] When encoding canonical wording into a SKILL.md (AI-only surface), it is written TERSELY — state trigger/steps/done just clearly enough to act; do NOT transcribe a CR's `change_summary` prose. Specs/templates (HUMAN-facing) keep full wording.

**Tooling gate (mandatory):**
- [ ] `py .ai-work/tooling/lint_aip.py --path <aip-file>` → **0 errors**

## Capture during AIP creation

### AIWS system issue capture

If AI discovers and fixes a problem during `create-aip` — a lint failure, a
missing required section, incorrect template guidance, a schema mismatch, or
any other AIWS system issue — **capture it as a candidate**.

- **If workspace already exists:** append to `08_capture_inbox.jsonl` immediately after the fix.
- **If no workspace yet** (AIP still being drafted): note the problem inline,
  then create the capture entry as the first action after `run-aip start`.

Use `type`: `aip_template_improvement_candidate` |
`run_aip_improvement_candidate` | `guideline_improvement_candidate` |
`tooling_opportunity_candidate`.

Set `candidate_kind: aiws_system_improvement`.

See: `.ai-work/procedural/wiki_candidate_capture_playbook.md` §15.

### Reusable artifact lookup miss → Pre-flight Pending Capture (MANDATORY)

Khi wiki lookup miss cho một artifact và artifact đó thuộc loại **reusable**
(template, process doc, checklist, shared spec, guideline — bất kỳ artifact nào
dùng làm "structural reference" hoặc "format template"), bắt buộc thực hiện ngay:

1. Trong AIP input table: đặt `Capture flag = [retrieval_gap]`
2. Append entry vào section `## Pre-flight Pending Captures` trong AIP file **NGAY LẬP TỨC**:
   ```
   - [PENDING] type="wiki_meta_update_candidate" candidate_kind="retrieval_improvement" artifact="<tên artifact>" lookup_query="<query đã dùng>" reason="<tại sao artifact này reusable>"
   ```
3. `run-aip start` sẽ sweep section này và import entry vào `08_capture_inbox.jsonl` tự động

**Dấu hiệu artifact reusable:**
- Tên có pattern: `TEMPLATE_*`, `*_TEMPLATE*`, `*_GUIDELINES*`, `*_CHECKLIST*`, `*_SPEC*`
- Nằm trong thư mục: `templates/`, `guidelines/`, `procedural/`, `09_processes/`
- Được dùng làm "structural reference" hoặc "format template" trong AIP input

**KHÔNG defer sang sau `run-aip start`.** Entry trong `## Pre-flight Pending Captures`
là evidence vật lý — tồn tại ngay trong AIP body dù workspace chưa được tạo.

## Rules
- **Multi-system (CR-AIWS-2026-06-017):** in a `multi_system: true` project, establish the task's **active system** up front (ask the HUMAN if unstated); pass `--system <id>` on every input lookup and carry it in the brief. If a lookup errors for a missing system, STOP and ASK — never auto-set/guess. Single-system → no effect.
- If uncertain between PLAN and EXEC → choose PLAN
- Do not create overly large AIPs
- AIP is stable control, not runtime notebook
- Each step should be materializable into Active Step Context
- Follow template section names exactly — do not rename required sections

### Mixed Governance Pattern

Khi AIP chứa cả no-CR steps (tooling/skills) lẫn CR-required steps (canonical docs):

1. **Governance Note** phải liệt kê RÕ cả 2 loại, ví dụ:
   - STEP-01 đến STEP-04: tooling/skill changes — không cần CR
   - STEP-05 đến STEP-06: canonical doc changes — HARD GATE (AIWS-Product-Owner approve; wiki-meta → Wiki-Manager)
2. **CR-required steps** dùng `Recommended Mode: Canonical-edit`
3. **HTML comment** phản ánh governance NGHIÊM NGẶT NHẤT trong AIP — không copy-paste từ AIP khác
4. **Governance Note** đặt ở đầu body, trước `## Objective`
