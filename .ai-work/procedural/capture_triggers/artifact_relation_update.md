# artifact_relation_update — Quan hệ giữa sources chưa có trong meta/index
- **type:** relation_candidate · **suggested_target:** wiki_meta · **timing:** normal
## When
AI phát hiện hai hoặc nhiều source artifact có quan hệ với nhau (depends_on, supersedes, companion_of, references...), nhưng quan hệ đó chưa được mô tả trong source meta hay index. Dấu hiệu: lookup/đọc nhiều source thấy chúng liên kết nhau mà meta/index không phản ánh.
## Capture as
candidate_kind `artifact_relation_update` — relation giữa các source cần được ghi vào meta/index relation fields.
## Suggested action
Sau HUMAN review, cập nhật relation fields trong source meta/index để phản ánh quan hệ đã phát hiện.
## Example
Khi build meta cho spec A, thấy A `references` spec B nhưng relation chưa có trong index → capture artifact_relation_update để bổ sung sau review.
## Notes
—
