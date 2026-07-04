# Lookup Key Strategy Spec — AI Work System MVP
Version: 0.1
Status: draft
Updated: 2026-05-25
Source: CR-D2, AIWS-Wiki-CR-Proposal-2026-05-25.md §3

---

## 1. Purpose

Spec này định nghĩa **chiến lược phân tầng lookup keys** trong Wiki Source Meta, nhằm cải thiện routing precision và giảm candidate list phình không kiểm soát.

Vấn đề cần giải quyết:
- Routing system hiện không phân biệt keyword identifier (T1 — high discrimination) vs section heading generic (T3 — low discrimination)
- Candidate list phình → giảm precision → tốn token AI
- Không có rule kiểm tra "keyword này có thực sự discriminatory không?"

Spec này bổ sung cho `WIKI_META_INDEX_SPEC` (artifact meta structure) và `Knowledge_Routing_Spec_MVP` (routing logic).

---

## 2. Tier Definitions

Mỗi lookup key trong meta được gán một tier phản ánh mức độ discriminatory của nó:

### T1 — Unique Identifier (Mandatory ≥1 per meta)

**Định nghĩa:** Keyword nhận dạng artifact/object duy nhất trong project scope.

**Đặc điểm:**
- Nếu search đúng keyword này, result set rất nhỏ (≤ N artifacts, N mặc định = 10)
- Không thể nhầm với artifacts khác nếu dùng standalone
- Stable qua thời gian (không thay đổi khi format drift)

**Ví dụ:**
- Function ID: `CB01001`, `F04`, `BA05001`
- Artifact ID: `SRC-DD-CB01001-FE`
- Canonical name: `発注処理`, `Order Processing`, `xử lý đặt hàng`
- Screen/API endpoint có ID unique: `/api/v1/orders/CB01001`

**Rule: T1 phải có ≥1 per meta.** Lint rule: `warn` khi meta thiếu T1 (không hard-fail — xem §6 Exceptions).

### T2 — Domain-Specific Term (Optional)

**Định nghĩa:** Keyword domain-specific nhưng không guaranteed unique, cần kết hợp với T1 hoặc qualifier để đạt precision tốt.

**Đặc điểm:**
- Hit rate có thể cao hơn T1 nhưng result set vẫn trong domain scope nhất định
- Thường là endpoint path, table name, alias, subsystem keyword

**Ví dụ:**
- Database table name: `t_order_header`, `m_product`
- API endpoint path: `/api/v1/orders`
- Subsystem: `purchasing`, `inventory`
- Japanese alias: `発注`, `在庫管理`

### T3 — Category Label (Optional)

**Định nghĩa:** Keyword phân loại artifact theo category nhưng generic và không phân biệt được artifact cụ thể.

**Đặc điểm:**
- Dùng standalone → hit quá nhiều artifacts (> N)
- Hữu ích như additional filter, không phải primary search term
- Thường là artifact type label, document category

**Ví dụ:**
- `detail_design`, `basic_design`, `api_contract`
- `review-relevant`, `testcase-relevant`
- `function`, `screen`, `table`

---

## 3. Rule K-1 — Discriminatory Value Test

**Rule:** Một keyword được phân loại T1 chỉ khi nó pass test:

> "Nếu search đúng keyword này trong wiki index, result set có nhỏ và đúng không?"

**Formal condition:** `search(keyword) → |result_set| ≤ N` trong scope hiện tại.

**Default N = 10.** Configurable per project/profile.

**Failure action:** Nếu keyword fail test → không được gán T1; phải pair với qualifier để đạt T1-level precision, hoặc gán T2/T3.

**Ví dụ:**
- `CB01001` → unique → T1 ✓
- `design` → hits hàng trăm artifacts → T3, không phải T1
- `ordering` → hits ~50 artifacts → T2 at best, pair với `CB01001` thành `CB01001 ordering` → T1 ✓

---

## 4. Rule K-2 — Tier Combination Rule

Nếu T1 của artifact cần nhiều tokens (ví dụ cụm tên dài), và project cho phép compound keys:

**Rule:** Compound T1 key = `{T2_qualifier}_{T1_identifier}` hoặc space-separated. Ví dụ:
- `ordering_CB01001` thay vì chỉ `CB01001` (nếu IDs có thể trùng cross-subsystem)
- `発注_CB01001` (Japanese + ID)

Compound key giữ nguyên tier T1 vì tổng hợp vẫn unique.

---

## 5. Rule K-3 — Anti-Pattern: Standalone Generic Section Heading

**Anti-pattern:** Section heading generic dùng standalone làm lookup key.

**Examples of violating patterns:**
- `design` (quá generic)
- `API` (quá generic)
- `search` (quá generic)
- `process` (quá generic)
- `list` (quá generic)

**Compliant alternatives:**
- `F04_API` thay vì `API`
- `CB01001_search` thay vì `search`
- `detail_design_fe` (combined với type) thay vì `design`

**Rule:** Keywords matching generic heading patterns KHÔNG được dùng standalone làm T1 hoặc T2. Phải pair với qualifier (function ID, subsystem, artifact ID).

Lint rule `lint_wiki.py --check-tiers` sẽ flag violation khi meta có keyword matching known generic patterns standalone.

---

## 6. Exceptions — T1 Mandatory Exemptions

Các trường hợp meta có thể không có T1 mà lint chỉ warn (không fail):

1. **Methodology spec artifact:** Spec có well-known canonical name (ví dụ `Knowledge_Routing_Spec_MVP`) — tên spec itself phục vụ như effective T1 ngay cả khi không phải function ID.
2. **External reference artifact:** Artifact từ nguồn bên ngoài không có project-level unique ID.
3. **Legacy artifact:** Artifact cũ chưa có ID convention.

Để claim exception, meta nên có field `t1_exception_reason: <reason>` để lint biết skip warning.

---

## 7. Tooling Impact

### 7.1. Profile schema extension

Profile YAML nên thêm optional field `lookup_key_tier_hints`:

```yaml
lookup_key_tier_hints:
  T1:
    - pattern: "[A-Z]{2}[0-9]{5}"   # function ID pattern (regex)
    - pattern: "SRC-[A-Z]+-.*"       # source ID pattern
  T2:
    - pattern: "t_[a-z_]+"           # table name pattern
    - pattern: "/api/v[0-9]/"        # API path pattern
  T3:
    - values: [detail_design, basic_design, api_contract, test_case]  # fixed enum
```

Profile-level hints cho phép `build_wiki_source_meta.py` tự động tag tier khi emit lookup keys.

### 7.2. Meta field: lookup key tier tagging

Trong wiki source meta, lookup keys nên được tagged với tier:

```yaml
lookup_keys:
  - key: CB01001
    tier: T1
  - key: ordering
    tier: T2
  - key: detail_design_be
    tier: T3
```

### 7.3. Lint rule

`lint_wiki.py --check-tiers`:
- WARN khi meta thiếu T1 (unless `t1_exception_reason` present)
- WARN khi T1 candidate keyword matches known generic heading pattern

### 7.4. Lookup tool: tier-aware scoring

`lookup_wiki_source.py` khi có tier info sẽ dùng scoring:
- T1 hit × 3.0 (boost)
- T2 hit × 1.5
- T3 hit × 1.0

Stop condition: nếu top-1 result là T1 exact match → return immediately, không expand thêm.

---

## 8. Relationship to Other Specs

- **[WIKI_META_INDEX_SPEC]** — `lookup_keys` field là nơi tier tags được embed
- **[Knowledge_Routing_Spec_MVP]** — Routing logic dùng tier scoring trong §4 (Discovery inputs)
- **[Artifact_Type_Taxonomy_Spec_MVP]** — `classification_signals.path_tokens` trong taxonomy đóng vai trò T2 hint candidates

---

## 9. Open Questions

- **OP-Q1:** N threshold = 10 có phù hợp với project lớn (1000+ artifacts) không? Cần calibrate per-project.
- **OP-Q2:** Khi meta đã built không có tier tags — có nên retroactively tag khi build index không? Tentative: yes (via rebuild index with --retag-tiers flag).

---

*Created: 2026-05-25 under AIP-EXEC-014 STEP-02. Source: CR-D2, AIWS-Wiki-CR-Proposal-2026-05-25.md §3.*
