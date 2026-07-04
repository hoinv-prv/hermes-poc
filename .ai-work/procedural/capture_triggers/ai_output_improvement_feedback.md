# ai_output_improvement_feedback — HUMAN feedback về chất lượng output AI
- **type:** guideline_improvement_candidate · **suggested_target:** guideline · **timing:** ⚡immediate
## When
HUMAN review một output AI tạo ra (draft, artifact, analysis, structured doc) và đưa corrective feedback: sai sót, thiếu phần, lỗi format, sai hướng tiếp cận, hoặc gợi ý hướng khác cho kết quả tốt hơn rõ rệt. Đây là bằng chứng gap giữa cái AI làm ra và cái thực sự cần. Capture khi: HUMAN explicit sửa/reject output và giải thích lý do; HUMAN đề xuất approach khác với kết quả tốt hơn đáng kể; hoặc xuất hiện recurring correction pattern lặp lại trong cùng một AIP.
## Capture as
candidate_kind: `ai_output_improvement_feedback`. Phải include nguyên văn feedback của HUMAN trong `content`. Chọn `type` theo bản chất gap:
- `guideline_improvement_candidate` → feedback chỉ ra quy tắc/hướng dẫn chung cần cải thiện (mặc định phổ biến).
- `run_aip_improvement_candidate` → vấn đề nằm ở cách thực thi AIP / quy trình run.
- `aip_template_improvement_candidate` → template AIP cần bổ sung/sửa.
- `notebook_note_candidate` → quan sát rời rạc, chưa đủ thành đề xuất canonical → để notebook.
## Suggested action
Review tại AIP close, gom recurring patterns qua các interaction, rồi propose cải thiện skill/guideline/template tương ứng (qua CR nếu chạm canonical product).
## Example
HUMAN: "Output thiếu acceptance criteria và dùng sai format bảng — lần sau bám template" → capture `guideline_improvement_candidate` kèm nguyên văn feedback.
## Notes
TIMING RULE: capture ngay khi feedback được đưa ra (⚡immediate), không đợi cuối step.
