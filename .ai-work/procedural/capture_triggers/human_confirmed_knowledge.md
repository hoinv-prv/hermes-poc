# human_confirmed_knowledge — HUMAN trả lời clarification tái dùng được
- **type:** qa_candidate · **suggested_target:** knowledge_hub_curated · **timing:** normal
## When
AI hỏi HUMAN vì Wiki/source không rõ ràng, và HUMAN trả lời bằng một rule, giải thích, exception, decision, hoặc cách diễn giải project-specific có thể tái dùng. Dấu hiệu: câu hỏi clarification được giải đáp dứt khoát, đáng để lần sau khỏi phải hỏi lại.
## Capture as
candidate_kind `human_confirmed_knowledge` — knowledge do HUMAN xác nhận khi nguồn không đủ rõ.
## Suggested action
Preserve HUMAN-confirmed knowledge thành candidate để future tasks không cần hỏi lại; chờ HUMAN review trước khi promote lên Knowledge Hub (curated).
## Example
HUMAN làm rõ: "Field X trong spec mặc định null khi import → trong dự án này luôn coi là 0" → capture làm `human_confirmed_knowledge`.
## Notes
—
