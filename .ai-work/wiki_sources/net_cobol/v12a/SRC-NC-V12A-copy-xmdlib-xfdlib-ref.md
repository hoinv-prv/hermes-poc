---
artifact_type: wiki_source_meta
source_id: SRC-NC-V12A-copy-xmdlib-xfdlib-ref
title: COPY OF XMDLIB / IN XFDLIB — curated reference (platform, compile error, migration)
source_type: curated_reference
artifact_locator: __PROJECT_ROOT__/.ai-work/wiki/reference/netcobol-copy-xmdlib-xfdlib.md
profile_id: curated_reference
status: active
updated_at: 2026-06-26
---
# Wiki Source Meta — COPY OF XMDLIB / IN XFDLIB — curated reference

## Summary
Curated reference (knowledge_class: curated) tổng hợp ngữ nghĩa COPY 書き方3 `OF XMDLIB | IN XFDLIB`: phân biệt XMDLIB (画面帳票定義体) vs XFDLIB (ファイル定義体), hỗ trợ platform, compile error JMN1062I-S / JMN1061I-S, option FORMLIB / FILELIB / `-m`, góc 互換性, và checklist review migration. Dùng khi điều tra compile error + review conversion design. KHÔNG thay manual gốc — verify_before_use.

## Knowledge Targets
- reference
- domain

## Lookup Keys
- XMDLIB
- XFDLIB
- OF XMDLIB
- IN XFDLIB
- COPY 書き方3
- COPY文
- 画面帳票定義体
- ファイル定義体
- 登録集原文
- JMN1062I-S
- JMN1061I-S
- FORMLIB
- FILELIB
- 定義体
- 互換性

## Source-Specific Hints
- Curated entry: `.ai-work/wiki/reference/netcobol-copy-xmdlib-xfdlib.md` (artifact_id WIKI-REF-NETCOBOL-COPY-XMDLIB-XFDLIB-001).
- §7 của entry liệt kê mâu thuẫn CHƯA chốt (XFDLIB trên bản 64bit) — đọc trước khi kết luận trong design.

## Related Sources
- **SRC-NC-V12A-nclr-7-1-copy** — role: clarifies — Diễn giải XMDLIB/XFDLIB của COPY文 §7.1 (platform, compile error, migration).
- **SRC-NC-V12A-cobol-language-reference-v12-2** — role: related_to — Tổng hợp từ COBOL文法書 V12.2.

## Cautions
- meta is not source-of-truth; always verify against the cited manual sections
- curated knowledge (entry use_rule: verify_before_use)
