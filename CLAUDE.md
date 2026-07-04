# CLAUDE.md  Ehermes-poc

Persistent project context. Read first in a new session.

## What this project is
Hermes PoC là dự án proof-of-concept để xây dựng và kiểm chứng quy trình làm việc với AI Work System trong bối cảnh phát triển phần mềm thực tế. Dự án tập trung vào chuẩn hóa workflow theo AIP, quản trị tri thức qua wiki source, và đảm bảo tính truy vết trong quá trình thực thi. Adopted **AI Work System MVP v1.0.5** as working methodology (since 2026-07-04). Live tree ềE`.ai-work/` tại project root.

## Adopted canonical knowledge

- **Methodology:** [AI Work System MVP](.ai-work/truth/canonical/methodology/)  E`source_of_truth`, `authoritative`. Override mọi `curated`/`reference`/`history` trên conflict.
- **Wiki operational guidance:** [Wiki Guideline Package + deltas](.ai-work/truth/canonical/wiki_guidelines/)  Ecomplement methodology. Trên conflict với spec, **spec wins**. Nav: [.ai-work/wiki/reference/wiki-guidelines.md](.ai-work/wiki/reference/wiki-guidelines.md).
- **Project Truth:** [SOP_MASTER](.ai-work/truth/SOP_MASTER.md), [AI_WORK_CONTRACT](.ai-work/truth/AI_WORK_CONTRACT.md), [AIP_ROOT](.ai-work/truth/AIP_ROOT.md).

Rule mơ hềEↁEspec wins trừ khi có Approved Deviation trong `AI_WORK_CONTRACT.md`.

## Core concepts
- **Truth** (`.ai-work/truth/`)  Eauthoritative, no silent rewrite.
- **AIP** (`.ai-work/aip/`  EROOT/PLAN/EXEC/LOCAL)  E**stable macro-control**, không phải runtime notebook.
- **Workspace** (`.ai-work/workspaces/<task-id>/`)  Eruntime execution memory (findings, draft, capture, final output).
- **Wiki** (`.ai-work/wiki/`)  Ecurated knowledge (domain/function/module/data/pattern/reference).
- **History** (`.ai-work/history/`)  Etrail/evidence/archive.

**Precedence:** Truth ↁEProject Wiki ↁELocal Wiki ↁECommon Wiki ↁEHistory (content) · SOP ↁEContract ↁEAIP_ROOT ↁEAIP_PLAN/EXEC ↁEGuidelines ↁESkills ↁEWiki ↁEWorkspace (artifact). Knowledge classes: `source_of_truth` ↁE`curated` ↁE`reference` ↁE`history`.

## Hot operational rules (MUST follow)

1. **Wiki Source lookup FIRST**  Ekhi user hỏi vềEconcept thuộc canonical knowledge của dự án: chạy `python .ai-work/tooling/lookup_wiki_source.py --query <keyword>` trước, đọc primary MD meta, mềEchapter/spec nếu cần.
   - **Match need ↁEtool (3 shapes):** FIND 1 doc = `lookup --query`; ENUMERATE one kind (mọi function/table) = `lookup --source-type <type> --slim`; TRAVERSE ("node liên quan gì / ai phụ thuộc") = `wiki_relations.py --relations <id>`. **Chain rule:** `wiki_relations` cần `source_id` (output của `lookup`)  Ekhông bắt đầu ềErelations khi chưa có id.
   - ❁E**Đừng `Read` nguyên `index.jsonl`/`relations.jsonl`** đềEenumerate  Edùng `--source-type --slim` / `wiki_relations` / grep.
   - **Index miss ↁEbắt buộc escalate:** retry `--mode semantic`, rồi raw Glob/Grep trong artifact dirs tool hint chềEra; không im lặng báo "không tìm thấy" sau 1 lần fail.
2. **Never read PDF/DOCX binaries**  Efollow `companion_of` pointer trong meta vềEprimary MD.
3. **Runtime state lives in Workspace**, không bao giềEtrong AIP body (findings/metrics/progress/decisions/draft ↁEworkspace files, không phải AIP sections).
4. **No silent drift from AIP**  Eđổi scope/output/objective phải thêm dated entry vào Re-plan Log; không edit earlier sections silently.
5. **No silent rewrite of Truth hoặc official Wiki**  Ecandidate ↁEreview ↁEapply.
6. **Capture first, curate later**  Eunknowns đi vào `08_capture_inbox.jsonl`, không đi thẳng vào wiki.
7. **SOP first**  Etask ngoài scope SOP/AIP_ROOT phải confirm với user.
8. **Lint là guardrail, không phải reviewer**  Ekhông ask tools auto-fix wiki/truth.
9. **`wiki_first` là default behavior**, không bắt buộc. Override chềEqua explicit HUMAN/rule/AIP instruction; ambiguous ↁE**clarify, không tự suy đoán**. Chi tiết + conflict rules: [wiki-guidelines.md](.ai-work/wiki/reference/wiki-guidelines.md).

## AIP stability rules (CRITICAL)

AIP là stable control artifact (AIP_Detail_Spec §2.3/§10/§11). Vi phạm biến AIP thành live working file  Eexplicitly forbidden.

- ❁E**Never tick `[x]` trong Done Criteria**  Edeclarative criteria, không phải progress checklist.
- ❁E**Never embed runtime metrics** trong AIP (counts, findings, decisions discovered during execution). Thuộc vềE`04_findings.md`.
- ❁E**Never silently edit earlier sections** đềEphản ánh scope change. Append Re-plan Log entry TRƯỚC khi edit.
- ❁E**`updated_at` không phải last-touched timestamp**  EchềEbump khi update-by-exception thực sự (§10.1).
- ✁EAllowed updates: objective / scope / expected outputs / major assumptions / explicit re-plan  Emỗi update bắt buộc có Re-plan Log entry.
- Linter (`lint_aip.py`) bắt `live_working_file`, `runtime_metric_in_aip`, missing sections. **Treat warnings as errors during review.**

## Execution protocol

Trước khi thực hiện bất kỳ non-trivial task nào (review, analysis, implementation, investigation...)  Enếu chưa có AIP, phải chạy `/create-aip` trước. Sau đó `/run-aip` đềEwire workspace. Không được làm thẳng trong chat. Làm việc trong workspace files, KHÔNG trong AIP. `/lint-all` trước khi finalize. Flow chi tiết: [.claude/skills/run-aip/SKILL.md](.claude/skills/run-aip/SKILL.md).

**Không cần AIP:** Ad hoc Q&A, câu hỏi đơn lẻ, tra cứu nhanh, research ngắn ↁEtrả lời thẳng trong chat.

## Tooling & Skills  Epointers

- **Tooling** [.ai-work/tooling/](.ai-work/tooling/)  EPython stdlib, no `pip install`. Full catalog: [README](.ai-work/tooling/README.md).
  - Find a document: `python .ai-work/tooling/lookup_wiki_source.py --query <keyword>`.
  - Find a source's relations (declared edges  Eone-hop, out + IN): `python .ai-work/tooling/wiki_relations.py --relations <id>`.
- **Skills** [.claude/skills/](.claude/skills/)  E`/create-aip`, `/run-aip`, `/init-workspace`, `/init-project`, `/point-step`, `/build-active-step-context`, `/build-wiki-source-meta`, `/lookup-wiki-source`, `/refresh-wiki-source-meta`, `/lint-all`. Mỗi skill có SKILL.md riêng.
- **Spec reference:** [Methodology](.ai-work/truth/canonical/methodology/) · [Wiki Guidelines](.ai-work/truth/canonical/wiki_guidelines/).

## Notes
- Python stdlib only. No `pip install`.
- Windows: tools force UTF-8 stdout (cp932-safe).
- User language: <điền preference  Emặc định Vietnamese + English mixed>.
- Always work from project root (nơi `.ai-work/` sits).


## AIWS Knowledge Sources (installed)

Khi user h?i v? AI Work System ho?c c?n t?o AIP template, tim trong cac source sau:

- Methodology: .ai-work/truth/canonical/methodology/
  Dung khi: cau h?i v? AIWS design, spec, khai ni?m, SOP flow
- Wiki Guidelines: .ai-work/truth/canonical/wiki_guidelines/
  Dung khi: cau h?i v? Knowledge Hub, wiki source, wiki meta, canonical guideline
- Preset Knowledge: .ai-work/preset_knowledge/
  Dung khi: t?o AIP m?i - tim AIP exec template ho?c sample phu h?p
  Nav: aip_exec/ (exec templates), aip_samples/ (samples), AIP_SELECTION_GUIDE.md

## Net COBOL Knowledge Source (manuals)

Khi user hoi ve Net COBOL (COPY, PERFORM, CALL, FILE I/O, SCREEN/FORM), uu tien wiki lookup tren Net COBOL meta/index:

- Luu y: bo manuals Net COBOL nay co tai lieu goc bang tieng Nhat. Khi lookup nen uu tien them tu khoa tieng Nhat de tang recall.

- Meta dir: .ai-work/wiki_sources/net_cobol/
- Index file: .ai-work/wiki_sources/index.net_cobol.jsonl
- Artifact root: manuals/net_cobol/

Lenh lookup khuyen nghi:

- Lexical:
  python .ai-work/tooling/lookup_wiki_source.py --query "COPY" --mode lexical --index .ai-work/wiki_sources/index.net_cobol.jsonl
- Semantic:
  python .ai-work/tooling/lookup_wiki_source.py --query "cach dung COPY trong Net COBOL" --mode semantic --index .ai-work/wiki_sources/index.net_cobol.jsonl
- Japanese keywords:
  python .ai-work/tooling/lookup_wiki_source.py --query "COPY文 REPLACING" --mode lexical --index .ai-work/wiki_sources/index.net_cobol.jsonl

Neu can tim ca Net COBOL va AIWS docs trong cung mot lan tra cuu, dung nhieu index:

- python .ai-work/tooling/lookup_wiki_source.py --query "COPY REPLACING" --index .ai-work/wiki_sources/index.net_cobol.jsonl,.ai-work/wiki_sources/index.aiws.jsonl
