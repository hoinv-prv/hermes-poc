# AIWS Change Request Spec (MVP) — v0.1

> **Status:** canonical methodology spec (MVP). **Authority:** the general, AIWS-wide standard for how Change Requests (CRs) are written, governed, approved, and applied for **all canonical AIWS documents**. `WIKI_CHANGE_REQUEST_SPEC` is the **wiki-meta-specialized profile** of this spec (see §18).
> **Placement:** `product/methodology/ai_work_system/20_specs/AIWS_Change_Request_Spec_MVP.md`.

## 1. Purpose & scope

A **Change Request (CR)** is the sanctioned, reviewable unit by which canonical AIWS content is changed. This spec defines the CR's structure, governance, and lifecycle for **every canonical AIWS doc type**:

- **Truth** — `SOP_MASTER`, `AI_WORK_CONTRACT`, `AIP_ROOT`.
- **Methodology & MVP specs** — `product/methodology/**` (incl. this spec).
- **Guidelines & wiki_guidelines** — `product/guidelines/**`, `product/wiki_guidelines/**`.
- **AIP templates** — `product/aip_templates/**`.
- **Procedural docs & doc-bearing skills** — `product/procedural/**`, the body of `*/SKILL.md`.

Drafting a CR is the sanctioned governance **entry point** (it is not itself a canonical edit). Applying a CR changes canonical content and is gated on AIWS-Product-Owner approval (§15).

## 2. When a CR is required (governance boundary)

| Surface | Class | Rule |
|---|---|---|
| Any canonical `product/` doc (specs, guidelines, methodology, wiki_guidelines, AIP templates, procedural, SKILL.md **body**) | **`cr_required`** | CR + AIWS-Product-Owner approval before apply (safety rule #8 / SOP §4.1). |
| Truth (`SOP_MASTER`/`AI_WORK_CONTRACT`/`AIP_ROOT`) | **`cr_required`** | As above; highest precedence content. |
| **Lint rules** (pass/fail or diagnostic logic) | **`cr_required`** | Frozen by CR-037 — even though they live in tooling code, a rule/diagnostic change is CR-routed. |
| Tooling code (dual-tree `.ai-work/tooling` ↔ `product/tooling`), excluding lint rules | **`no_cr`** | Tooling-edit-flow: edit `.ai-work` → verify → mirror byte-identical to `product`. AIP may still be required by project rule. |
| AIP files, runtime workspace state | **`no_cr`** | Not canonical product; AIP Re-plan Log / workspace are the record. |

- **`mixed`** — a CR whose content spans both classes labels each surface explicitly (e.g. a spec note = `cr_required` + a SKILL.md sweep = `no_cr` dual-tree).
- **Drafting any CR is always `no_cr`** (the entry point), regardless of what it later applies.

## 3. Foundational principles

- **3.1 No direct canonical edits from an ad hoc finding.** Canonical changes flow through a CR.
- **3.2 AIWS-Product-Owner controls the update.** Apply requires explicit approval **and** an explicit request to apply (an approved CR alone is insufficient — SOP §5 Rule C). AI never self-approves nor self-applies.
- **3.3 Output-driven by default.** A CR proposes a concrete change with evidence, not open-ended discussion.
- **3.4 AI-executable.** A CR is specific enough that an apply-AIP can execute it deterministically (exact targets, before/after, guardrails).

## 4. AIWS change_type vocabulary

Practical, extensible set (pick the closest; add a clear new value + rationale if none fits):
`add_curated_knowledge` · `modify_spec` · `add_spec` · `refine_lint_precision` · `tooling_update` · `process_template_update` · `guideline_update` · `governance_rule` · `deprecate` · `migrate`.

(The wiki profile keeps its own wiki-meta-specific `change_type`/`target_layer` enums — §18.)

## 5. CR structure

### 5.1 Frontmatter
`cr_id` · `title` · `request_type` · `change_type` · `requester` · `reviewer_or_product_owner` · `status` · `created_at` · `needs_human_confirmation_after_draft` · `driving_source` · `related_cr` (optional list).

### 5.2 Body sections
`Context` · §1 Request identity · §2 Target · §3 Requested change · §4 Source basis · §5 Proposed update direction · §6 Guardrails · §7 Maturity/grounding · §8 §15 propagation checklist · §9 Governance Note · §10 Alternatives weighed · **Apply Outcome** (added at apply) · **Revision History**.

## 6. Field reference (essentials)

- **`cr_id`** — `CR-AIWS-YYYY-MM-NNN` (§10 allocation). **`title`** — one line, names the change + drivers.
- **`request_type`** — coarse class (`tooling_update` / `process_template_update` / `spec_change` / …). **`change_type`** — §4 vocabulary.
- **`reviewer_or_product_owner`** — usually `aiws_product_owner`. **`status`** — §16 lifecycle.
- **`driving_source`** — where the change came from (capture id, triage report, re-plan, IR) — verbatim/traceable.
- **`related_cr`** — sibling CRs sharing target files or lineage (see §11.1, §11.2).
- **`needs_human_confirmation_after_draft: true`** — drafting applies nothing.

## 7. Minimal mandatory fields

A conformant CR MUST carry: `cr_id`, `title`, `request_type` (or `change_type`), `requester`, `reviewer_or_product_owner`, `status`, a **Target** (every path), a **Requested change** (summary + reason + expected outcome), and a **Source basis**. Missing any → not ready for review.

## 8. Lightweight CR form

For a small, fully AI-executable change, the body may collapse to: Context + Target + Requested change (before/after) + Source basis + Guardrails + a one-line §15 N/A. Frontmatter mandatory fields still apply. (Larger or node-model/vocab changes use the full §5.2 body.)

## 9. Targets & dual-tree apply discipline

- **Enumerate every touched path** in §2 Target (no "etc.").
- **Dual-tree:** tooling and SKILL.md-body changes apply byte-identical to both trees (`.ai-work/...` ↔ `product/...`); verify `diff -q`. For a **SKILL.md body** edit, §2 Target MUST list **both** `.ai-work/procedural/skills/<name>/SKILL.md` **and** `product/procedural/skills/<name>/SKILL.md` (the `product/skills/<name>/SKILL.md` pointer is unchanged) — listing one tree under-scopes the apply *(CR-AIWS-2026-06-037 C2)*.
- **Re-anchor before edit; never pin line numbers** — re-grep OLD wording at apply (it may have drifted). Run a pre-close OLD-wording sweep.

## 10. id & registry discipline  *(OP-A, ruled 2026-06-19)*

- **`cr_id = CR-AIWS-YYYY-MM-NNN`. NNN is MONTH-SCOPED** — unique within `YYYY-MM`, restarting each month (de-facto: May 2026 ran 002–038; June 2026 restarted at 001).
- **Allocate cross-branch — never single-branch `max+1`.** In a multi-branch program, CR ids (and AIP ids) are allocated against an **authoritative view across all branches** (e.g. `git log --all` scan, or `allocate_aip_id.py` for AIP ids). A single-branch `max+1` causes collisions: **CAP-001** — `CR-025` was independently used on two branches for different content, and a hand-picked AIP id (`114/115`) collided with sibling branches, forcing a renumber.
- **Do not pin a not-yet-existing sibling id** (CR or AIP) — reference by stable description + the stable id you do have (see §11).
- Burned/superseded ids are not reused (record supersession instead).
- **Scan working-tree ∪ git — never committed-only or counter-only** *(CR-AIWS-2026-06-037 C1)*. A `git log` scan of only the current checkout, or a counter-only allocate, misses ids **applied concurrently / just-committed on another branch / uncommitted in another worktree** — exactly how `CR-AIWS-2026-06-034` collided (renumbered → `035`). Union (a) the working tree on disk (`product/change_requests/**` + `.ai-work/aip/**`, incl. `applied|drafts|rejected`), (b) `git log --all`, (c) the counter. `allocate_aip_id.py` now unions disk + `git log --all` + counter and tolerates `-slug` artifact_ids.

## 11. CR-authoring conventions  *(absorbed from AIP-093)*

- **11.1 Concurrent-CR coordination (CAP-073-02).** Before finalizing a draft CR, grep open/draft CRs for shared target files. On overlap, add a reciprocal `related_cr` noting region-ownership and that **apply must be coordinated/sequenced**. (Complements §12's within-CR propagation with across-concurrent-CR coordination.)
- **11.2 Stable sibling-refs (CAP-073-01).** When a CR references a sibling CR's edit, anchor on a **stable region description + the sibling's `cr_id`**, never the sibling's internal change-number (`Cn`, unstable until applied).
- **11.3 Defer-to-apply-AIP (CAP-055-03).** A CR Apply-Outcome that defers work references **"the apply AIP for this CR"**, never a specific not-yet-existing AIP id (the `cr_id` is stable; the applying-AIP id is not).
- **11.4 Numbered-test labels (CR-AIWS-2026-06-037 C2).** When a CR adds a **numbered test case** to a test file, do NOT pin the label in the CR — verify the **next-free** label against the target file at apply (a `T5` clash forced a `T6` rename), or reference the assertion by **name**, not number.

## 12. Node-model / vocab-change propagation checklist (§15)

When a CR changes the **node model** or a **validated vocabulary** (e.g. a `META_REQUIRED`/`INDEX_REQUIRED` field, a `SOURCE_TYPE_VOCAB`/profile, an index projection, a node-kind), it MUST resolve the propagation checklist (promoted from / linked to `WIKI_CHANGE_REQUEST_SPEC §15`): each affected surface is marked propagated-plan or N/A-with-reason. A CR that touches neither marks §15 **N/A**.

## 13. Lint gate

`apply_gates` MUST require `/lint-all` clean (0 errors) before the CR flips to `applied`. Tooling changes additionally verify dual-tree byte-identity + fixtures/regression. Verification fixtures cited in `apply_gates` MUST be **in-repo** — never a consumer/downstream-project artifact (rule #9). When ≥2 approved CRs co-edit shared files, prefer ONE **batch apply-AIP by file-pass** (edit each shared file once) over one-AIP-per-CR. *(CR-AIWS-2026-06-034)*

## 14. Version / changelog / install-package impact

- A canonical-doc change may warrant a version/changelog note in the affected package's manifest/baseline.
- **Auto-ship:** `product/**` payload sections are copied wholesale into the install package — a new/edited file under such a section ships on the next build with no build-script change (confirm the section is wholesale-copied before scoping a packaging edit).
- **Content-only doc additions do NOT bump the package version per-addition** *(CR-AIWS-2026-06-037 C5)*. A new doc added to a versioned package (e.g. a `wiki_guidelines` core guideline) is **registered** (manifest / canonical-doc index / navigator) but the package version + version-stamped install/rollout file labels **rebadge together at the next package build/release** — not per content addition (avoids a label-rename cascade on every doc).

## 15. CR + AIWS-Product-Owner approval flow

```
draft (no_cr)  →  status: proposed  →  AIWS-Product-Owner APPROVE (status: approved_for_ai_update)
              + explicit "apply" request (SOP §5 Rule C)  →  APPLY (cr_required, dual-tree)
              →  status: applied  +  Apply Outcome (truthful post-mortem)
```
AI never self-approves nor self-applies. A rejected CR is revised and re-presented (never partially applied).

## 16. Status lifecycle

`proposed` → `approved_for_ai_update` → `applied`; plus `rejected`. **Folder (CR-AIWS-2026-06-034):** drafts in `drafts/`; proposed/approved CRs in the main `product/change_requests/` folder; once **applied**, moved to `applied/` (the archive).

## 17. Source-basis rule

A CR is grounded in **project source** (file/line, capture, triage, IR, prior CR). Any AI inference beyond the source is **clearly separated** (in §5/§7), so a reviewer can see what is grounded vs proposed. External-IR claims are adversarially verified against canonical before being folded in.

## 18. Relationship to WIKI_CHANGE_REQUEST_SPEC

- **This spec is the general AIWS-wide CR authority.** `WIKI_CHANGE_REQUEST_SPEC` is its **wiki-meta-specialized profile**: it adds wiki-meta-specific `change_type`/`target_layer` enums and the canonical §15 propagation checklist (which this spec promotes/links).
- Where this spec and the wiki profile overlap, the wiki profile governs **wiki-meta** CRs; this spec governs **all other** canonical AIWS CRs. WCR carries a matching relation note.
- **Two approval roles (by scope) — CR-AIWS-2026-06-031:** AIWS-canonical CRs (this spec) are approved by the **AIWS-Product-Owner** (the AIWS design project only); wiki-meta CRs (the WCR profile) by the **Wiki-Manager** (common to every project using AIWS). The roles are parallel, not hierarchical; the AIWS side uses `reviewer_or_product_owner`, the wiki side `reviewer_or_wiki_manager`.
- **Downstream projects (consuming AIWS):** must NOT apply changes to AIWS canonical docs/tools themselves — only PoC/test locally, then raise a CR **upstream** to the AIWS project, where the **AIWS-Product-Owner** decides. (Wiki changes within a consuming project remain that project's Wiki-Manager's call.)

## 19. Worked AIWS examples

- **Ex.1 — methodology-spec edit (`cr_required`):** a CR modifying `AIP_Detail_Spec_MVP §6.3`; Target = the spec path; before/after wording; apply via an apply-CR AIP after approval.
- **Ex.2 — lint-precision (`cr_required` via CR-037):** `CR-AIWS-2026-06-029` narrowed `capture_refs` + added a `lint_aip` diagnostic — tooling code, but CR-routed because lint rules are frozen; applied dual-tree with fixtures.

## 20. Out of scope (this spec)

- Back-compat migration / normalization of the existing ~50 `CR-AIWS-*` files.
- Building a CR **document template** or a CR-id **allocation tool** (this spec may recommend them; building is follow-on).
- Rewording Truth or AIP templates to cite this spec (follow-on CR).
- **Applied-CR folder (resolved by CR-AIWS-2026-06-034):** applied CRs are moved to `applied/`; drafts in `drafts/`.

## 21. Relationships

- **Truth:** `SOP_MASTER §4.1/§5`, `AI_WORK_CONTRACT §2/§4/§5` (this spec cites and conforms to them; does not reword them here).
- **`AIP_Detail_Spec_MVP`** (apply-CR AIPs instantiate `AIP_EXEC_APPLY_CR_TEMPLATE`).
- **`WIKI_CHANGE_REQUEST_SPEC`** (wiki-meta profile — §18).

## 22. Completion criteria

This spec is complete when: it covers the §1 doc types; the governance boundary (§2) is unambiguous; the field reference + mandatory set (§6/§7) match de-facto practice; id discipline (§10) codifies month-scoped + cross-branch allocation; the 3 conventions (§11) are stated; the approval flow + lifecycle (§15/§16) match SOP; and it is registered in the wiki source index + methodology indexes with `WIKI_CHANGE_REQUEST_SPEC` carrying the reciprocal profile note.
