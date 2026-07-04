---
name: run-aip
description: Orchestrate AIP execution — start / resume / jump-to-step / status / list
user-invocable: true
---

# SKILL: run-aip

## Purpose
Prepare workspace state for AIP execution without manually calling
`init_workspace`, `set_current_step`, and `build_active_step_context`.
Does not execute step content — only points the workspace at the right step.

In addition to preparing runtime state, this skill must keep AI aware of
**Wiki / Knowledge Hub candidate capture** during execution. When the AI notices
knowledge gaps, reusable patterns, source relationships, useful references, or
HUMAN-confirmed decisions, it should record a candidate in the workspace Capture
Inbox for later HUMAN review.

This skill must **not** directly promote knowledge into the Wiki / Knowledge Hub.
Promotion remains curated and HUMAN-controlled.

## Tool
`.ai-work/tooling/run_aip.py`

## Subcommands
- `start` — create workspace, point at STEP-01 (or `--step`), materialize ASC
- `resume` — rebuild ASC for current pointer step (or `--step`)
- `step` — jump pointer to a specific step and rebuild ASC
- `status` — show current AIP / workspace / pointer state, including Capture Inbox counts
- `list` — show all steps in the AIP

> **Workspace resolution (CR-AIWS-2026-06-015 F5).** `resume`/`status` find the workspace by: explicit `--task-id` → reverse-scan `.current_step.json` back-link (`aip_id`) → AIP frontmatter `runtime_workspace` pointer → `today()` fallback — so resume works ACROSS DAYS (no more `today()`-derived mis-resolve). If >1 live workspace maps to one AIP, run-aip **STOPS and asks** (possible bug) — pass `--task-id` to choose; it never silent-picks. `start` writes a **write-once** `runtime_workspace` provenance pointer into the AIP. `status` prints the capture-triage rollup (`build_aip_index.py --list-untriaged` lists offenders repo-wide). AIP ids come from `allocate_aip_id.py` (see create-aip), never hand-picked. **CR-015 v2:** NEW workspaces are created under `.ai-work/workspaces/<account_id>/` (account_id from account_info.yaml); the reverse-scan is RECURSIVE so it finds per-account + legacy-flat workspaces; new AIPs live under `.ai-work/aip/<account_id>/<kind>/` (legacy flat untouched). **CR-AIWS-2026-06-057 (Phase 1):** this runtime workspace is the executor-agnostic **Task Workspace** — when an `aip_driven` agent run is started with `--aip <this AIP>`, the agent run REUSES this AIP's Task Workspace (no second workspace; see the agent pack / `aiws-agent`).

### Pre-start AIP validation (mandatory before `start`)

Before running `run-aip start <AIP>`:
1. Run `py .ai-work/tooling/lint_aip.py --path <aip-file>`
2. **If errors:** stop — fix AIP first, do not run `start` until 0 errors
3. **If warnings only:** proceed, note warnings in workspace `04_findings.md`

Rationale: An AIP with format errors (wrong section name, missing step fields, step numbering gaps)
produces an empty or incorrect Active Step Context. Fail fast at `start` is better than silent failure
during execution.

## PRE-FLIGHT GATE — Artifact Lookup (HARD GATE)

⛔ **HARD GATE — về việc xác định WHERE một canonical artifact nằm ở đâu, KHÔNG phải re-lookup thừa.** run-aip chạy từ các input **ĐÃ RESOLVED** của AIP (Flow 2b). Với MỖI RD/BD/DD/spec dùng làm input, quyết định theo case:

1. **Đã resolved trong AIP → mở thẳng.** Nếu input có **path cụ thể** (trong `## Required Wiki Inputs`, `Inputs` của step, hoặc `## References to Read First`) và KHÔNG bị đánh dấu Deferred → mở path đó. **KHÔNG cần** `lookup_wiki_source.py` — đã resolve lúc create-aip rồi.
2. **Chỉ lookup khi cần** — chạy `py .ai-work/tooling/lookup_wiki_source.py --query "<keyword>"` **CHỈ KHI**: (a) AIP đánh dấu item là **Deferred lookup** / "tìm trong wiki"; hoặc (b) input nêu tên artifact **không có path cụ thể**; hoặc (c) path đã ghi **không còn resolve trên disk** (moved/renamed) — wiki index là authority tìm ra vị trí mới (staleness fallback). **Scope (CR-AIWS-2026-06-052):** bare `--query` dùng default scope `project,aiws`; `local` opt-in + `--authorized human` (rule #11); raw (un-registered) search cần `--include-raw`+`--authorized` — thiếu → tool refuses (halt-and-ask).
3. **Index miss ở lookup (2) → escalate** — retry `--mode semantic`; chỉ fallback Glob/Grep sau khi cả 2 miss, và ghi rõ đã escalate.

❌ **VẪN FORBIDDEN:**
- Glob/Grep để **dò tìm** một artifact mà AIP KHÔNG resolve (không cho path) trước khi thử lookup
- Suy luận path từ artifact khác user đã cung cấp (vd: user cho path DD → tự Glob BD/RD cùng thư mục)

## Flow
1. (New task) `run-aip start <AIP-ID> --title "..."` → creates workspace, materializes ASC
1b. **[PENDING CAPTURE SWEEP — MANDATORY]** Ngay sau `start`, trước khi đọc ASC:
    - Đọc AIP file, tìm section `## Pre-flight Pending Captures`
    - Nếu có entries `[PENDING]` → import từng entry vào `08_capture_inbox.jsonl`; mark entry thành `[IMPORTED YYYY-MM-DD]` trong AIP section
    - Nếu section không tồn tại hoặc 0 entries pending → log "No pending captures found in AIP"
    - Bước này KHÔNG skip được — log bắt buộc dù 0 matches
2. Read `00c_active_step_context.md` → work within workspace files
2b. **[TASK LENS — follow the AIP]** run-aip executes from the AIP's already-resolved `## Required Wiki Inputs` + `## References to Read First` — it does NOT re-search. The ASC `active_task_lens` (from the AIP's `## Selected Task Lens / Mode`) is used only to: (a) **order** the reading of those inputs (preset `register_priority`/`expansion_priority` as a HINT — read broader/verify raw when correctness needs it); and (b) resolve items the AIP lists under **Deferred lookups** (`doc + lens`) — nothing else. No-Lens / nothing deferred ⇒ reading unchanged. See the **PRE-FLIGHT GATE** above for *how* to open those resolved inputs (resolved path → read directly, no re-lookup; `lookup_wiki_source.py` only for Deferred / path-less / stale-on-disk). Ref: `Task_Lens_Spec_MVP` §D/§F.
3. During step execution, use Wiki / Knowledge Hub first when relevant, then verify with source artifacts when needed
4. **Capture Wiki candidates inline — the moment a candidate is discovered**, append to `08_capture_inbox.jsonl` per the **Wiki Candidate Capture Playbook** (see below). Do NOT batch captures to step end or AIP close.
5. `run-aip step <AIP-ID> --step STEP-NN` → advance pointer, rebuild ASC. At step boundary do a final sweep for items missed mid-stream.
6. Repeat until done
6b. **[FINAL CAPTURE SWEEP — MANDATORY]** Before running `lint_all.py`: sweep toàn bộ work của AIP (diffs, findings, execution artifacts) để tìm candidates còn sót. Append vào `08_capture_inbox.jsonl`. Log closing check summary vào workspace findings. Bước này KHÔNG skip được — dù capture inbox đã đầy hay task đơn giản.
7. Run `lint_all.py` before finalizing
8. Before closing the task, run `run-aip status <AIP-ID>` and check unresolved Runtime Queue items and untriaged Capture Inbox items

## Rules
- do not use `run-aip` to modify the AIP file itself
- do not tick `[x]` in AIP Done Criteria — progress lives in workspace
- always read `00c_active_step_context.md` first before touching runtime files
- `--force` on `start` wipes existing workspace — use only when prior attempt is discardable
- do not directly promote candidates into Wiki / Knowledge Hub unless the AIP step explicitly allows it and HUMAN confirmation is available
- Capture Inbox is for candidates and findings with possible future value; it is not a replacement for Wiki / Knowledge Hub
- candidate capture should be useful but not noisy: capture only when there is clear Knowledge Value
- capture **immediately on discovery** — append to `08_capture_inbox.jsonl` the moment you notice a candidate; do not defer to end-of-step or end-of-AIP. End-of-step is a safety sweep, not the primary capture point.
- capture **problems discovered and fixed during execution** (playbook §15) — a silently-fixed problem that is not captured is an improvement opportunity lost

## Wiki-first preflight at HARD GATE

Before posing a HARD GATE clarifying question about a concept that may exist in canonical knowledge, AI MUST run a 3-step preflight:

1. **Lookup** — Run `python .ai-work/tooling/lookup_wiki_source.py --query <concept>` for the question's topic keyword.
2. **Read primary meta** — If any Wiki Source matches, read the primary MD meta; if the meta points to a wiki entry under `product/wiki_guidelines/` (or a project-local materialization under `.ai-work/wiki/`), read that entry's relevant section.
3. **Surface conflicts inside the gate question** — If existing canonical guidance conflicts with the proposed direction (or makes the question moot), state that conflict *in the HARD GATE question itself* so HUMAN can adjudicate. Do NOT pose a question that ignores existing wiki guidance.

**Cite the wiki path** in the AIP step's `Applicable Guidelines` field — list the wiki entry path (e.g., `product/wiki_guidelines/core/specs/<entry>.md` or `.ai-work/wiki/<entry>.md`). This makes the preflight visible to the lint rule `wiki_first_preflight_at_hard_gate` in `lint_aip.py` and to future reviewers.

**Explicit opt-out:** If the topic genuinely has no wiki coverage, add `wiki:none` as a bullet in `Applicable Guidelines` to confirm the preflight was performed and returned no matches. Do NOT silently omit the citation.

**Anti-pattern (observed in AIWS deployments):** A HARD GATE step asks HUMAN about a convention (e.g., a naming pattern) without first consulting the relevant wiki entry, which already carries authoritative guidance that contradicts the proposed direction. The mismatch surfaces only mid-implementation, forcing a retrofit and wiki revision. The preflight rule surfaces the conflict at the gate, before commitment.

See also: [`wiki_candidate_capture_playbook.md`](../../wiki_candidate_capture_playbook.md) §"When to Capture" — preflight gaps are themselves a `retrieval_improvement` capture trigger.

## Step execution heuristics

### Section-number conflict heuristic (next-available adjacent)

When an OP-decision or AIP step references a target-doc section by number (e.g., "add to §10") and the target doc **already occupies** that section number with unrelated content, apply the **next-available adjacent** rule:

1. Pick the lowest unoccupied adjacent section number (`§N+1`, then `§N+2`, …).
2. Preserve original intent — inline location near related content; do not relocate to an unrelated part of the doc.
3. Document the choice in **two places**:
   - **AIP Re-plan Log** — append entry citing the conflict and the chosen number.
   - **Target-doc Revision History** — record the new section number with cross-link back to the OP-decision.
4. **Do NOT re-clarify with HUMAN** unless the *intent itself* is ambiguous. Section numbers are interpretive; intent is authoritative. When in doubt, prefer the spirit-of-OP over the letter-of-OP per AIWS Methodology.

**Example (heuristic-applied):** An OP-decision directs "Inline §10 migration guide in TARGET.md", but §10 is already occupied by an unrelated section added in a prior revision. The author places the migration guide as §11 (next-available adjacent), preserving inline single-source-of-truth intent without overwriting prior content. Saves a re-clarify cycle.

See also: [`wiki_candidate_capture_playbook.md`](../../wiki_candidate_capture_playbook.md) §"When to Capture" — repeated section-number conflicts in similar contexts may indicate a doc-structure issue worth capturing as `task_pattern_candidate`.

## Wiki Candidate Capture (during execution)

During AIP execution, AI must actively look for **two categories** of candidates
and append to `08_capture_inbox.jsonl` when Knowledge Value criteria are met:

**Category 1 — Wiki / Knowledge Hub candidates:**
Knowledge gaps, reusable patterns, source relationships, useful references, or
HUMAN-confirmed decisions that may improve the Knowledge Hub.

**Category 2 — AIWS system improvement candidates:**
Problems discovered and fixed during step execution — lint failures, schema
mismatches, incorrect skill/playbook/guideline guidance that caused a real
mistake, tooling bugs. A silently-fixed problem is an improvement opportunity
lost. Capture it immediately after the fix.

Use `type`: `aip_template_improvement_candidate` |
`run_aip_improvement_candidate` | `guideline_improvement_candidate` |
`tooling_opportunity_candidate`. Set `candidate_kind: aiws_system_improvement`.

The detailed runtime guidance (when-to-capture triggers, kinds, JSON record
format, Step Closing Check) lives in a dedicated playbook:

- **Operational playbook** (runtime triggers, kinds, format, closing check):
  `.ai-work/procedural/wiki_candidate_capture_playbook.md`
- **Eligibility theory** (candidate vs canonical, suggestion thresholds):
  `product/wiki_guidelines/core/specs/WIKI_CANDIDATE_SUGGESTION_RULE.md`
- **Capture/triage principles**:
  `.ai-work/procedural/capture_and_triage_rules.md`

See playbook §15 for full guidance on Category 2 (AIWS system improvements).

This skill must **not** directly promote knowledge into the Wiki / Knowledge
Hub. Promotion remains curated and HUMAN-controlled.

## When closing an AIP

Per [AIP_Detail_Spec_MVP §5.6](../../../methodology/ai_work_system/20_specs/AIP_Detail_Spec_MVP.md), allowed `status` enum is `[draft, active, done, archived]`. To close a finished AIP, set `status: done` (NOT `completed` — see create-aip SKILL.md "Frontmatter conventions"). After updating status, run:

```
python .ai-work/tooling/lint_aip.py --path .ai-work/aip/exec/<aip-id>.md
```

A clean run confirms the AIP is fully spec-compliant before being marked done.

### Final Capture Sweep (MANDATORY — before status flip `active → done`)

Trước khi flip status `active → done`, bắt buộc thực hiện Final Capture Sweep:

1. **Review toàn bộ scope** — diffs, findings, execution artifacts của mọi step trong AIP
2. **Tìm candidates còn sót** — knowledge gaps, patterns, tool issues, guideline improvements chưa được capture mid-stream
3. **Append vào `08_capture_inbox.jsonl`** — mọi candidate có Knowledge Value còn sót
4. **Log closing check summary** vào workspace findings: tổng số entries mới, tổng entries trong inbox, trạng thái
5. **Không skip** — dù task đơn giản hay capture inbox đã có nhiều entries

Nếu AIP có dedicated "Final Capture Sweep" step (STEP-XX): thực hiện qua step đó. Nếu không có: thực hiện inline trước khi flip status.

### Re-plan Log: pre-applied change scope (precision rule)

Khi ghi Re-plan Log entry về changes được **pre-apply ngoài AIP flow**, dùng granularity **change-level**, không phải step-level:

- ❌ `STEP-02 đổi sang 'verify + document'` — không đủ khi một step chứa nhiều independent changes
- ✅ `Pre-applied: [change A, change B] — NOT pre-applied: [change C]`

**Anti-pattern (observed in AIP-EXEC-025):** Re-plan Log entry ghi "STEP-02 pre-apply" nhưng chỉ Final Capture Sweep (Flow 6b + "When closing" gate) được pre-apply — IR-001 start sweep (step 1b) KHÔNG được pre-apply. Khi verify tại STEP-02, AI assumed toàn bộ step đã done → phát hiện miss và phải apply thêm.

**Rule:** Trong cùng Re-plan Log entry, liệt kê explicitly:
- `Pre-applied: [danh sách từng change]`
- `NOT pre-applied: [danh sách changes còn lại của step đó]`

### Target-spec attribution check (before status flip `active → done`)

Before flipping AIP status `active → done`, run a 3-step attribution check:

1. **Grep target specs** for this AIP-ID in source-of-truth docs and wiki entries touched in scope:

   ```bash
   grep -rIn "<AIP-ID>" product/ .ai-work/wiki/ .ai-work/truth/
   ```

2. **For each hit**, verify the AIP's Re-plan Log or Done Criteria reflects the change the target spec attributes. If a target spec attributes content to this AIP-ID but the AIP's Re-plan Log is silent → **append a Re-plan Log entry first**, then flip status.

3. **Scope:** This check applies to **explicitly-attributed target specs only** — specs whose body or Revision History row names the AIP-ID. Broader `applies_to` frontmatter sweep is intentionally out of scope; raise as separate skill update if a recurring need surfaces.

**Anti-pattern (observed in AIWS deployments):** A prior AIP session authored a target-spec revision and the target spec attributed the change to "AIP-EXEC-XXX STEP-NN HUMAN approval YYYY-MM-DD". The AIP itself stayed `status: draft` with an empty Re-plan Log until the next session discovered the drift while preparing to author the next revision from scratch.

See also: [`capture_and_triage_rules.md`](../../capture_and_triage_rules.md) §"AIP closing — capture/triage-related items" for the capture/triage-side bullet of this check.
