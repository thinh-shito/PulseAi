# Kế hoạch Thiết kế Diagram Logic dự án PulseAI

## Tổng quan
Tài liệu này vạch ra kế hoạch xây dựng các sơ đồ logic (diagram) cho dự án PulseAI nhằm mục đích chia sẻ và giải thích cấu trúc hệ thống cho các contributor khác. Các sơ đồ sẽ được lưu dưới định dạng **Mermaid (UML)** trong thư mục `docs/` để dễ dàng quản lý bằng Git và tích hợp thẳng vào tài liệu Markdown của dự án.

## Loại dự án
- **WEB & BACKEND** (Next.js 14 App Router + FastAPI + LangGraph + PostgreSQL + Celery/Redis)

## Tiêu chí thành công
1. Tạo file tài liệu [docs/architecture-and-logic-flow.md](file:///Users/dothinhtpr247gmai.com/Desktop/PulseAi/docs/architecture-and-logic-flow.md) chứa toàn bộ các diagram logic.
2. Các sơ đồ UML/logic bao gồm:
   - **System Component Diagram**: Sơ đồ tổng quan kiến trúc hệ thống và kết nối các thành phần.
   - **Prior Authorization (PA) Activity & Sequence Diagram**: Luồng xử lý chi tiết từ lúc upload ghi chú lâm sàng đến khi xuất file PDF kết quả Prior Authorization (bao gồm ẩn danh dữ liệu PHI, xử lý đa tác vụ AI qua LangGraph và phê duyệt Human-in-the-Loop).
   - **Authentication & JWT Flow Diagram**: Cơ chế đăng nhập, tạo, làm mới token (Access/Refresh Token) và blacklist token khi đăng xuất.
   - **Database Class Diagram / ERD**: Quan hệ giữa các bảng chính trong DB (`User`, `Workflow`, `ClinicalRecord`, `AuditLog`, `PATemplate`).
3. Cú pháp Mermaid của toàn bộ diagram hoạt động chính xác và hiển thị tốt trên các trình xem Markdown hỗ trợ Mermaid (như GitHub).

## Danh sách công nghệ sử dụng
- **Mermaid.js**: Ngôn ngữ tạo sơ đồ bằng text code (dễ dàng chỉnh sửa bởi contributor).
- **Markdown**: Ngôn ngữ trình bày tài liệu.

## Cấu trúc thư mục mới
```plaintext
docs/
└── architecture-and-logic-flow.md  # File tài liệu chứa toàn bộ sơ đồ logic và kiến trúc dự án
```

## Kế hoạch chi tiết (Task Breakdown)

### T1: Thiết kế các sơ đồ Mermaid UML
- **Mô tả**: Viết mã nguồn Mermaid cho 4 sơ đồ logic cốt lõi của PulseAI.
- **Người thực hiện**: `project-planner` / `backend-specialist`
- **Kỹ năng sử dụng**: `architecture`, `clean-code`
- **Độ ưu tiên**: Cao (P0)
- **Đầu vào -> Đầu ra -> Kiểm thử**:
  - *Đầu vào*: Thông tin cấu trúc dự án từ [PROJECT.md](file:///Users/dothinhtpr247gmai.com/Desktop/PulseAi/PROJECT.md) và [ARCHITECTURE.md](file:///Users/dothinhtpr247gmai.com/Desktop/PulseAi/ARCHITECTURE.md).
  - *Đầu ra*: Mã nguồn Mermaid hoàn chỉnh cho 4 loại diagram.
  - *Kiểm thử*: Xác thực cú pháp từng sơ đồ Mermaid để đảm bảo không bị lỗi cú pháp render.

### T2: Tạo file tài liệu và tích hợp sơ đồ
- **Mô tả**: Tạo file [docs/architecture-and-logic-flow.md](file:///Users/dothinhtpr247gmai.com/Desktop/PulseAi/docs/architecture-and-logic-flow.md), viết lời giải thích chi tiết kèm theo các đoạn mã Mermaid tương ứng.
- **Người thực hiện**: `documentation-writer` / `project-planner`
- **Kỹ năng sử dụng**: `documentation-templates`
- **Độ ưu tiên**: Cao (P1)
- **Đầu vào -> Đầu ra -> Kiểm thử**:
  - *Đầu vào*: Các sơ đồ Mermaid từ T1 và thông tin giải thích luồng nghiệp vụ.
  - *Đầu ra*: File `docs/architecture-and-logic-flow.md` hoàn thiện.
  - *Kiểm thử*: Kiểm tra cấu trúc tài liệu, các liên kết nội bộ, và định dạng Markdown.

---

## ✅ PHASE X: XÁC THỰC CUỐI CÙNG
- [x] Xác nhận file [docs/architecture-and-logic-flow.md](file:///Users/dothinhtpr247gmai.com/Desktop/PulseAi/docs/architecture-and-logic-flow.md) được tạo thành công trong thư mục `docs/`.
- [x] Chạy kiểm tra cú pháp Mermaid trong file tài liệu.
- [x] Chạy audit tài liệu bằng checklist.py để đảm bảo tính nhất quán của hệ thống.

## ✅ PHASE X COMPLETE
- Lint: ✅ Pass
- Security: ✅ No critical issues
- Build: ✅ Success
- Date: 2026-06-11

