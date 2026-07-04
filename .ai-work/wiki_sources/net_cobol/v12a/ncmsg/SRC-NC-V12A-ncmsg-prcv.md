---
artifact_type: wiki_source_meta
source_id: SRC-NC-V12A-ncmsg-prcv
title: PRCV（2.10） — メッセージ集 V12.2
source_type: net_cobol_vendor_manual
artifact_locator: __PROJECT_ROOT__/manuals/net_cobol/NetCOBOL_64bit_V12a/NetCOBOL V12.2 メッセージ集/NetCOBOL V12.2 メッセージ集.md
profile_id: net_cobol
status: active
updated_at: 2026-06-26
---
# Wiki Source Meta — PRCV（2.10） — メッセージ集 V12.2

## Summary
Dải mã message PRCV (翻訳時/compile-time) — struct meta; mỗi code cụ thể tra demand-driven trong section 2.10.

## Knowledge Targets
- reference
- domain

## Lookup Keys
- PRCV
- 翻訳時メッセージ
- 2.10
- JMN
- compile error

## Source-Specific Hints
- Section 2.10 «PRCV» trong NetCOBOL V12.2 メッセージ集.md.
- Tra full nội dung 1 code: `python .ai-work/tooling/lookup_netcobol_message.py --code <CODE>` (vd JMN1117 / JMP0001 / ODBC-2244 / PRCV-ER001). Output = full section trích từ index dựng sẵn `project_wiki/netcobol_message_index.jsonl` (メッセージ集 V12.2) — KHÔNG cần Read cả file 2.5MB.

## Related Sources
- **SRC-NC-V12A-messages-v12-2** — role: part_of — Thuộc メッセージ集 V12.2 (manual gốc).
- **SRC-MIG-POLICY-cobol-compile** — role: related — Bảng tra compile error (cross-ref).
