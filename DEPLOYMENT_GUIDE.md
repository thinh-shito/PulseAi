# Hướng dẫn Deploy dự án PulseAI thành 1 File duy nhất

Dự án **PulseAI** sử dụng kiến trúc nhiều thành phần (Multi-service architecture) bao gồm:
1. **Frontend**: Next.js (TypeScript)
2. **Backend**: FastAPI (Python)
3. **Database**: PostgreSQL 16
4. **Cache/Queue**: Redis 7
5. **Worker**: Celery (Python)

---

## 📦 Phương án 1: Đóng gói thành File Docker Image Archive (`.tar.gz`) — Khuyên dùng (Offline/Air-gapped)
Phương án này nén tất cả mã nguồn, môi trường chạy, PostgreSQL, Redis, cấu hình môi trường, và dữ liệu mẫu (seed data) vào một file lưu trữ Docker duy nhất. Thích hợp cho việc deploy ngoại tuyến (offline) hoặc chuyển giao dự án nhanh gọn.

### 📜 Tệp liên quan:
* [docker-compose.prod.yml](docker-compose.prod.yml)
* Thư mục Backend: [src-backend](src-backend)
* Thư mục Frontend: [src-frontend](src-frontend)
* Script đóng gói: [scripts/package_offline.sh](scripts/package_offline.sh)

---

### 🚀 Các bước Đóng gói (Packaging)
Tại máy phát triển (development machine), chỉ cần chạy một lệnh duy nhất:
```bash
./scripts/package_offline.sh
```
Script sẽ tự động:
1. Build mã nguồn Frontend (Next.js) và Backend (FastAPI) trong môi trường Production.
2. Tải các Docker Image nền chính thức (`postgres:16-alpine` và `redis:7-alpine`).
3. Lưu và nén toàn bộ 4 Docker Image này vào tệp `pulseai-release.tar.gz`.
4. Đóng gói tệp nén này cùng với `docker-compose.yml`, `.env`, và script cài đặt `deploy.sh` thành tệp **`pulseai-deployment.zip`** duy nhất ở thư mục gốc dự án.

---

### 💻 Các bước Cài đặt & Khởi chạy trên Máy chủ đích (Server)

1. **Copy** tệp `pulseai-deployment.zip` lên máy chủ đích.
2. **Giải nén** tệp zip:
   ```bash
   unzip pulseai-deployment.zip -d pulseai-deployment
   cd pulseai-deployment
   ```
3. **Khởi chạy ứng dụng**:
   ```bash
   ./deploy.sh
   ```

> [!IMPORTANT]
> Script `deploy.sh` sẽ tự động thực hiện:
> * Nạp toàn bộ các Docker Image offline vào máy chủ đích.
> * Tạo tệp cấu hình môi trường `.env` từ tệp mẫu.
> * Khởi động tất cả các container.
> * Đợi PostgreSQL sẵn sàng nhận kết nối, sau đó tự động chạy **Database Migrations** (`alembic upgrade head`) để tạo cấu trúc bảng.
> * Tự động chạy **Seed script** để khởi tạo các tài khoản lâm sàng mẫu.

---

### 🔑 Tài khoản đăng nhập mặc định (Môi trường Dev/Test):

Sau khi chạy thành công lệnh `./deploy.sh`, bạn có thể truy cập Frontend tại `http://localhost:3000` và đăng nhập bằng một trong các tài khoản sau:

| Tài khoản | Email | Mật khẩu | Quyền (Role) |
|---|---|---|---|
| **Bác sĩ (Doctor)** | `doctor@pulseai.hospital` | `DoctorPass123!` | `DOCTOR` (Bắt đầu workflow và duyệt Prior Auth) |
| **Quản trị viên (Admin)** | `admin@pulseai.hospital` | `AdminPass123!` | `ADMIN` (Quản lý user, xem audit logs) |
| **Người xem (Viewer)** | `viewer@pulseai.hospital` | `ViewerPass123!` | `VIEWER` (Chỉ xem trạng thái & báo cáo) |
