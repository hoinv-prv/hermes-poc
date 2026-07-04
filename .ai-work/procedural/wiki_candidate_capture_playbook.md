# Wiki / Knowledge Hub Candidate Capture Playbook

Operational quick-reference: **bắt gì · capture lúc nào · ghi thế nào**.
Chi tiết + ví dụ từng trigger: file riêng trong [`capture_triggers/`](capture_triggers/) — mỗi dòng bảng dưới map sẵn **case → file**.
Eligibility theory: `product/wiki_guidelines/core/specs/WIKI_CANDIDATE_SUGGESTION_RULE.md`.

## Cách tổ chức (đọc 1 lần)
- File này là **index hành động**: bảng 19 trigger + record format + closing check. Đủ để AI quyết định capture mà không cần mở gì thêm.
- Cần chi tiết/ví dụ của 1 trigger → cột `# · fragment` đã chỉ sẵn file → Read **đúng** `capture_triggers/<slug>.md`, không mò, không load cả khối.
- **Thêm use-case mới:** (1) tạo `capture_triggers/<new_slug>.md` theo template; (2) thêm 1 dòng vào bảng dưới. KHÔNG đụng fragment cũ.

## Scope
- Active trong **mọi AIP execution** (bất cứ task nào cần workspace), không chỉ khi `/run-aip`.
- AI **chỉ suggest candidate** — KHÔNG tự promote/refresh canonical Wiki (HUMAN-controlled).
- Lưu vào: `.ai-work/workspaces/<TASK-ID>/08_capture_inbox.jsonl` (append 1 JSON/dòng).
- `run-aip status <AIP-ID>` báo capture counts + số cần triage (status=captured) cho workspace của AIP (CR-AIWS-2026-06-015 F4); `build_aip_index.py --list-untriaged` liệt kê mọi AIP còn capture mở (repo-wide).
- **AI Agent Instance (CR-AIWS-2026-06-042 C1):** instance chạy **dưới một AIP** (run sở hữu workspace) → append capture vào project inbox `08_capture_inbox.jsonl` theo đúng trigger + record format dưới đây, y như mọi in-workspace work (tái dùng cơ chế AIWS, CLAUDE.md #7). Instance chạy **không có AIP** → giữ capture trong **instance queue** (`candidate_queue.jsonl`, package-/instance-level) — KHÔNG chảy vào project inbox cho tới khi instance đó chạy dưới một AIP hoặc HUMAN promote. Promotion → confirmed memory / official wiki vẫn **HUMAN-gated** ở cả hai nhánh.

## Capture khi nào
**Capture** nếu giúp ≥1: task tương lai nhanh/chính xác/nhất quán hơn · giảm đọc lại raw source ·
cải thiện search/meta/discovery · lưu rule/decision HUMAN-confirmed · lộ quan hệ source chưa có trong meta ·
tránh lặp lỗi · thành pattern/playbook tái dùng · cơ hội tooling.
**Không capture** nếu: chỉ task-local tạm · không có giá trị tái dùng · suy đoán không bằng chứng ·
trùng candidate đã có · quá nhỏ.

## 19 Triggers — capture as
Cột **`# · fragment`** = map case → file chi tiết (đọc đúng file, khỏi mò). ⚡ = capture ngay (không dồn cuối step).

| # · fragment | Khi... | `candidate_kind` | `type` điển hình | `suggested_target` |
|---|---|---|---|---|
| [1 · missing_wiki_knowledge](capture_triggers/missing_wiki_knowledge.md) | Cần info, wiki không có nhưng raw source có | `missing_wiki_knowledge` | `wiki_update_candidate` | `wiki_meta` |
| [2 · artifact_relation_update](capture_triggers/artifact_relation_update.md) | Phát hiện quan hệ giữa sources chưa có trong meta/index | `artifact_relation_update` | `relation_candidate` | `wiki_meta` |
| [3 · summary_layer_candidate](capture_triggers/summary_layer_candidate.md) | Đọc lại cùng source nhiều lần (chỉ cần summary/meta) | `summary_layer_candidate` | `summary_candidate` | `wiki_meta` |
| [4 · new_reference_candidate](capture_triggers/new_reference_candidate.md) | Tìm thấy reference/source-of-truth hữu ích mới | `new_reference_candidate` | `wiki_update_candidate` | `knowledge_hub_reference` |
| [5 · human_confirmed_knowledge](capture_triggers/human_confirmed_knowledge.md) | HUMAN trả lời 1 clarification tái dùng được | `human_confirmed_knowledge` | `qa_candidate` | `knowledge_hub_curated` |
| [6 · retrieval_improvement](capture_triggers/retrieval_improvement.md) | Wiki có nhưng khó tìm (alias/index/title yếu) | `retrieval_improvement` | `wiki_meta_update_candidate` | `wiki_meta` |
| [7 · task_pattern_candidate](capture_triggers/task_pattern_candidate.md) | Phát hiện task pattern tái dùng | `task_pattern_candidate` | `playbook_candidate` | `guideline` |
| [8 · best_practice_anti_pattern](capture_triggers/best_practice_anti_pattern.md) | Best practice / anti-pattern | `best_practice_candidate` / `anti_pattern_candidate` | `guideline_improvement_candidate` | `guideline` |
| [9 · knowledge_quality_issue](capture_triggers/knowledge_quality_issue.md) | Knowledge quality issue (outdated/conflict/low-conf) | `knowledge_quality_issue` | `finding_candidate` | `wiki_meta` |
| [10 · decision_candidate](capture_triggers/decision_candidate.md) | Decision chưa được lưu | `decision_candidate` | `insight` | `knowledge_hub_curated` |
| [11 · glossary_candidate](capture_triggers/glossary_candidate.md) | Glossary/terminology cần chuẩn hoá | `glossary_candidate` | `wiki_update_candidate` | `knowledge_hub_curated` |
| [12 · onboarding_candidate](capture_triggers/onboarding_candidate.md) | Onboarding knowledge (đọc gì trước, entry point) | `onboarding_candidate` | `guideline_improvement_candidate` | `guideline` |
| [13 · tooling_opportunity_candidate](capture_triggers/tooling_opportunity_candidate.md) | Cơ hội tooling/automation cho việc cơ học lặp lại | `tooling_opportunity_candidate` | `tooling_opportunity_candidate` | `future_backlog` |
| [14 · cross_project_knowledge_candidate](capture_triggers/cross_project_knowledge_candidate.md) | Knowledge tái dùng được liên dự án | `cross_project_knowledge_candidate` | `future_backlog_candidate` | `future_backlog` |
| [15 · aiws_system_improvement](capture_triggers/aiws_system_improvement.md) ⚡ | Fix lỗi skill/template/tooling/playbook ngay khi run | `aiws_system_improvement` | `aip_template_improvement_candidate` · `run_aip_improvement_candidate` · `guideline_improvement_candidate` · `tooling_opportunity_candidate` | `aip_template`/`run_aip`/`guideline`/`tooling` |
| [16 · ai_output_improvement_feedback](capture_triggers/ai_output_improvement_feedback.md) ⚡ | HUMAN feedback về chất lượng output AI | `ai_output_improvement_feedback` | `guideline_improvement_candidate` · `run_aip_improvement_candidate` · `aip_template_improvement_candidate` · `notebook_note_candidate` | `guideline`/`notebook` |
| [17 · recurring_failure_defense_in_depth](capture_triggers/recurring_failure_defense_in_depth.md) | Recurring failure (N≥2) trong AIWS flow | `task_pattern_candidate` | `playbook_candidate` | `guideline` |
| [18 · wiki_source_refresh_needed](capture_triggers/wiki_source_refresh_needed.md) ⚡ | Sửa/phát hiện-đổi tài liệu wiki đã đăng ký/canonical | `wiki_source_refresh_needed` | `wiki_meta_update_candidate` (dùng `wiki_update_candidate` nếu canonical doc) | `wiki_meta` (hoặc `knowledge_hub_curated`) |
| [19 · object_relation_capture](capture_triggers/object_relation_capture.md) ⚡ | Lúc build/refresh meta cho artifact → nhận biết OBJECT nó mô tả + quan hệ object↔artifact (representation) + quan hệ object↔object (domain x:, kể cả suy luận) | `object_relation_capture` | `wiki_update_candidate` | `wiki_meta` |

Chọn `candidate_kind` gần nhất, đừng đẻ kind trùng lặp. Không có → kind mới rõ ràng + giải thích trong `content`.
Cột `# · fragment` link thẳng tới detail (Suggested action / Example / Notes) của trigger đó.

## Record format
Append 1 JSON object/dòng vào `08_capture_inbox.jsonl`. Compact nhưng có bằng chứng.

> **LINTER CONTRACT** (`lint_workspace.py`) — 6 field bắt buộc: `id`, `type`, `title`, `content`, `status`, `suggested_target`
> (`suggested_target` thiếu = warning; 4 field còn lại + `type` thiếu = error).

```json
{"id":"CAP-001","type":"wiki_meta_update_candidate","title":"...","content":"... (kèm evidence inline)",
 "status":"captured","suggested_target":"wiki_meta","candidate_kind":"wiki_source_refresh_needed",
 "knowledge_value":"high","discovered_at":"YYYY-MM-DD","step":"STEP-NN","reusable":true}
```

**Enum hợp lệ:**
- `type`: `insight` · `qa_candidate` · `summary_candidate` · `playbook_candidate` · `relation_candidate` ·
  `deferred_note` · `wiki_update_candidate` · `finding_candidate` · `wiki_meta_update_candidate` ·
  `aip_template_improvement_candidate` · `run_aip_improvement_candidate` · `guideline_improvement_candidate` ·
  `source_representation_issue` · `future_backlog_candidate` · `notebook_note_candidate` · `tooling_opportunity_candidate`
- `suggested_target`: `knowledge_hub_curated` · `knowledge_hub_reference` · `wiki_meta` · `aip_template` ·
  `run_aip` · `guideline` · `skill` · `notebook` · `future_backlog` · `tooling` · `history_only` · `discard`
- `status`: `captured` (mới) · `triaged` (đã review) · `promoted` · `archived` · `discarded` · `deferred` · `retained_local`

Còn untriaged → HUMAN/reviewer xử lý trước khi đóng task hoặc ở curation pass kế.

## Step Closing Check
Trước khi đóng mỗi step, tự hỏi — yes bất kỳ → append candidate:
1. Không tìm thấy trong wiki nhưng tìm ở nơi khác? (§1)
2. Hỏi HUMAN 1 điều nên tái dùng? (§5) · Đọc lại cùng source nhiều lần? (§3)
3. Phát hiện quan hệ source / reference / source-of-truth chưa được ghi? (§2,§4)
4. Wiki khó retrieve / cần alias-index-overview? (§6)
5. Task pattern · best practice · anti-pattern · decision đáng lưu? (§7,§8,§10)
6. Conflict / outdated / low-confidence knowledge? (§9)
7. Fix lỗi skill/playbook/template/tooling? (§15) · HUMAN feedback về output? (§16)
8. Sửa/thấy đổi tài liệu wiki đã đăng ký/canonical → cần refresh meta/index/object? (§18 — scope: artifact meta/index)
9. Build/refresh meta cho artifact → đã nhận biết object nó mô tả + quan hệ object↔artifact (representation) và object↔object (domain x:, kể cả suy luận) → đề xuất HUMAN author object node + edges chưa? (§19)

## See Also
- Map case → file: bảng **19 Triggers** phía trên (cột `# · fragment`). Chi tiết từng trigger: [`capture_triggers/`](capture_triggers/) (19 fragment, mỗi use-case 1 file).
- `WIKI_CANDIDATE_SUGGESTION_RULE.md` — eligibility theory · `capture_and_triage_rules.md` — nguyên tắc capture
- `queue_rules.md` — queue conventions
