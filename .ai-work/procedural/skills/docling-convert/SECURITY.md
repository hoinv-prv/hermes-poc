# Bảo mật — docling-convert skill

---

## Thư viện docling

**Nhà phát triển:** IBM Research (Zurich), thuộc Linux Foundation AI & Data. Mã nguồn mở, giấy phép **MIT**.

**Dữ liệu của bạn không rời khỏi máy.** Docling xử lý hoàn toàn cục bộ — không gửi file hay nội dung lên server bên ngoài theo mặc định. Kết nối internet chỉ cần một lần khi tải AI model (từ Hugging Face của IBM). Sau đó chạy offline hoàn toàn.

**Lỗ hổng đã biết — cần cập nhật:**

| CVE | Mức độ | Vấn đề | Khắc phục |
|---|---|---|---|
| CVE-2026-24009 | Cao | RCE qua YAML loader trong `docling-core` | `docling-core >= 2.48.4` |
| CVE-2026-31247 | Cao | XXE trong backend JATS XML | `docling >= 2.95.0` |
| CVE-2026-31248 | Cao | XXE trong backend METS XML | `docling >= 2.95.0` |
| CVE-2026-44520 | Trung bình | SSRF trong `docling-graph` | Không cài nếu không dùng |

Hai lỗi XXE chỉ ảnh hưởng khi xử lý JATS/METS XML từ nguồn không tin cậy — không liên quan đến PDF/DOCX/XLSX thông thường.

---

## Bản thân skill này

**Tổng thể: Rủi ro thấp, phù hợp dùng nội bộ.**

**Điểm tốt:**
- Không có network call trong bất kỳ script nào
- Không dùng `shell=True` — không có nguy cơ shell injection
- Không `eval()` / `exec()` trên nội dung file
- XML từ Excel parse bằng Python 3 stdlib — mặc định chặn XXE
- Excel COM đóng file đúng cách trong `finally` block — không để process treo

**Rủi ro cần lưu ý:**

1. **Excel COM có thể chạy macro** (`screenshot_sheets.py`)
   Script mở file bằng Excel thật qua `win32com`. Nếu `.xlsm` chứa macro độc hại, Excel có thể tự chạy dù `DisplayAlerts = False`. Chỉ dùng với file từ nguồn tin cậy.

2. **Output path không giới hạn**
   `--out-dir` có thể trỏ đến bất kỳ đâu user có quyền ghi. Chấp nhận được cho tool nội bộ, nhưng cần lưu ý nếu tích hợp vào pipeline tự động nhận input từ bên ngoài.

3. **File `.xlsm` output giữ nguyên macro**
   Skill copy XML từ file gốc — nếu gốc có macro, output cũng có. Đây là behavior đúng, nhưng cần biết khi chia sẻ output.

**Không phải rủi ro (dù trông có vẻ vậy):**
- `subprocess` trong `roundtrip.py` — dùng list args, không phải string → an toàn
- `~/.docling_convert_config.json` — chỉ lưu preference, không có gì nhạy cảm
- Base64 decode từ Markdown — chỉ decode PNG, không execute

**Khuyến nghị:**

| Tình huống | Cần làm gì |
|---|---|
| File từ bên ngoài (email, upload) | Không dùng `screenshot_sheets.py` trước khi scan virus |
| Pipeline tự động | Thêm whitelist thư mục output |
| Dùng nội bộ với file của team | An toàn như hiện tại |
