# best_practice_anti_pattern — Best practice / anti-pattern
- **type:** guideline_improvement_candidate · **suggested_target:** guideline · **timing:** normal
## When
AI phát hiện một cách làm tốt lặp lại được (good practice) hoặc một sai lầm cần tránh (mistake to avoid) trong quá trình thực thi. Dấu hiệu: nhận ra "lần sau nên làm thế này" hoặc "cái này gây lỗi, đừng lặp lại".
## Capture as
Chọn candidate_kind theo ngữ cảnh:
- **best_practice_candidate** → khi là good practice lặp lại được, nên khuyến khích.
- **anti_pattern_candidate** → khi là mistake to avoid, cần cảnh báo.
## Suggested action
Sau HUMAN review, bổ sung reusable guidance / checklist vào guideline tương ứng.
## Example
"Luôn chạy `/lint-all` trước khi finalize AIP" (best_practice) — đưa vào checklist guideline thay vì tự ý apply.
## Notes
Slug best_practice_anti_pattern bao trùm cả best_practice_candidate lẫn anti_pattern_candidate; chọn nhánh dựa trên tính chất quan sát được.
