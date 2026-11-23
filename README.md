# Xianglingo — Hệ thống luyện thi chứng chỉ HSK 1–4 tích hợp trợ giảng AI

Dự án Luận văn tốt nghiệp xây dựng nền tảng học tập, ôn luyện theo lộ trình và thi thử HSK 1–4 với trợ giảng AI **Xiang**.

---

## 1. Cấu trúc thư mục tổng thể

```text
HSK_AI/
├── docs/                                   # Đặc tả chuẩn (bám sát bố cục báo cáo LVTN)
│   ├── 01_muc_tieu_pham_vi.md              # Phạm vi HSK 1–4, phân quyền 3 vai trò, ranh giới Backend – AI
│   ├── 02_quy_tac_nghiep_vu.md             # Quy tắc nghiệp vụ cốt lõi và luồng xử lý chi tiết
│   ├── 03_thiet_ke_csdl.md                 # Sơ đồ CSDL, từ điển dữ liệu 24 bảng + 4 View, chuẩn hóa 3NF/BCNF
│   └── 04_kich_ban_kiem_thu.md             # Kịch bản kiểm thử chấp nhận (AT01–AT48)
├── xianglingo_schema.sql                   # Lược đồ MySQL 8.4 đầy đủ (24 bảng + 4 View + dữ liệu danh mục gốc)
├── backend/                                # Máy chủ API (Python, FastAPI, SQLAlchemy Core, PyMySQL)
│   ├── app/
│   │   ├── api/router.py                   # Điểm gắn duy nhất cho toàn bộ module API dưới tiền tố /api
│   │   ├── core/                           # Cấu hình hệ thống (JWT, Google OAuth, SMTP)
│   │   ├── database/                       # Kết nối phiên MySQL (session.py) và sinh mã gốc phiên bản (root_id.py)
│   │   ├── integrations/ai/                # Cổng kết nối AI tập trung (config, singleton OpenAI client, prompts)
│   │   ├── security/                       # Xác thực JWT, kiểm tra vai trò (Học viên, Giảng viên, Quản trị), IP
│   │   ├── storage/                        # Lưu trữ media công khai (/media) và học liệu riêng tư (private_uploads)
│   │   └── modules/                        # Các phân hệ nghiệp vụ độc lập theo miền (Domain Modules)
│   │       ├── common/                     # Xử lý lỗi dịch vụ, trợ giúp SQL và Pydantic schema dùng chung
│   │       ├── grading/                    # Bộ chấm điểm khách quan & nạp câu hỏi/phương án dùng chung toàn hệ thống
│   │       ├── auth/                       # Đăng ký, đăng nhập, xác minh email, quên mật khẩu, Google OAuth
│   │       ├── account_profile/            # Hồ sơ học viên, chuỗi ngày học, năng lượng, KN và mục tiêu
│   │       ├── hsk_levels/                 # Quản lý danh mục cấp độ HSK 1–4
│   │       ├── vocabulary/                 # Ngân hàng từ vựng và thẻ từ (flashcards)
│   │       ├── questions/                  # Ngân hàng câu hỏi có phiên bản (versioning) và kiểm tra ràng buộc
│   │       ├── practice_authoring/         # Soạn thửa đất, bài ôn luyện và kiểm tra cuối thửa (Giảng viên)
│   │       ├── exam_authoring/             # Soạn và xuất bản đề thi thử HSK (Giảng viên)
│   │       ├── materials/                  # Học liệu PDF/ảnh/audio và danh mục liên kết học tập bên ngoài
│   │       ├── practice/                   # Lộ trình ôn luyện, làm bài, kiểm tra vượt thửa/vượt cấp & học thử (Khách)
│   │       ├── mock_tests/                 # Phòng thi thử bấm giờ, tính điểm quy đổi HSK, thống kê & gợi ý lộ trình
│   │       ├── mistake_notebook/           # Sổ tay câu sai lặp lại ngắt quãng và nhiệm vụ hằng ngày
│   │       ├── ai_tutor/                   # Trợ giảng AI Xiang (theo lượt làm bài và theo hạn mức ngày/IP)
│   │       ├── writing_review/             # Giảng viên duyệt và chấm đè câu tự luận
│   │       ├── content_reports/            # Học viên báo lỗi câu hỏi & Giảng viên xử lý
│   │       ├── lecturer_dashboard/         # Tổng quan số liệu nội dung cho Giảng viên
│   │       ├── search/                     # Từ điển tra nhanh từ vựng HSK
│   │       ├── survey/                     # Khảo sát đầu vào (đang chuyển giao sang bài đánh giá thích ứng 8 câu)
│   │       └── admin/                      # Quản trị tài khoản, phân quyền vai trò và nhật ký hệ thống
│   ├── scripts/                            # Script nâng cấp CSDL và nạp dữ liệu mẫu (seed)
│   ├── tests/                              # Kiểm thử tự động (unit/ và integration/)
│   ├── .env.example                        # Mẫu biến môi trường Backend
│   └── requirements.txt                    # Danh sách thư viện Python
└── frontend/                               # Giao diện người dùng (React 19, React Router 7, Vite 8)
    ├── src/
    │   ├── app/App.jsx                     # Định tuyến tổng thể cho Công khai, Học viên, Giảng viên, Quản trị
    │   ├── layouts/                        # Khung bố cục theo từng vai trò (Public, Student, Lecturer, Admin)
    │   ├── routes/RequireRole.jsx          # Bảo vệ đường dẫn theo vai trò đăng nhập
    │   ├── shared/                         # Thành phần dùng chung toàn ứng dụng (không phụ thuộc một tính năng lẻ)
    │   │   ├── api/                        # HTTP client chuẩn hóa và hook gọi dữ liệu useRequest
    │   │   ├── components/                 # Icon, HanziText, LessonParts, SentenceBuilder, BackButton...
    │   │   ├── hooks/                      # Hook toàn cục (useTheme)
    │   │   ├── navigation/                 # Header, Footer, cấu hình menu theo vai trò
    │   │   ├── styles/                     # CSS cho các component dùng chung
    │   │   └── utils/                      # Hàm định dạng ngày/kích thước/mediaUrl (format.js), danh hiệu KN (rank.js)
    │   ├── styles/                         # Biến màu thiết kế (tokens.css) và kiểu nền tảng (global.css)
    │   └── features/                       # Từng tính năng tách riêng theo cấu trúc chuẩn:
    │       └── <ten_tinh_nang>/
    │           ├── api/                    # Hàm gọi REST API của riêng tính năng
    │           ├── components/             # Thành phần giao diện con của tính năng
    │           ├── hooks/                  # React hooks riêng của tính năng
    │           ├── pages/                  # Các màn hình gắn trực tiếp vào Router
    │           ├── styles/                 # CSS của tính năng
    │           └── utils/                  # Hàm tính toán/nhãn hiển thị nội bộ của tính năng
    └── .env.example                        # Mẫu biến môi trường Frontend
```

---

## 2. Nguyên tắc tổ chức mã nguồn (Quy ước dễ học – dễ bảo trì – dễ nâng cấp)

1. **Một chiều phụ thuộc rõ ràng**:
   - **Backend**: `endpoints/` (nhận HTTP, kiểm tra đầu vào) → `services/` (quy tắc nghiệp vụ & giao dịch CSDL) → `grading/` / `common/` / `integrations/`. Các phân hệ ngang hàng (`practice`, `mock_tests`, `mistake_notebook`, `ai_tutor`) dùng chung logic chấm và nạp câu qua `app/modules/grading/`, **không import chéo lẫn nhau**.
   - **Frontend**: `features/*` được phép import từ `shared/`, `layouts/`, `assets/` và `auth/` (ngữ cảnh đăng nhập); các thành phần hiển thị câu hỏi/chữ Hán dùng chung đặt tại `src/shared/components/` và `src/shared/utils/`.
2. **Tập trung cổng gọi AI (`backend/app/integrations/ai/`)**:
   - Mọi tính năng dùng AI đều đi qua `client.py` (`chat_completion`, `json_completion`).
   - Luôn đóng hoặc `rollback()` phiên đọc MySQL **trước khi** gọi AI để không giữ kết nối CSDL trong lúc chờ mạng.
3. **Backend giữ quyền quyết định nghiệp vụ**:
   - Chấm câu khách quan, tính điểm, trừ năng lượng, cộng KN, kiểm tra điều kiện mở khóa cấp/thửa đều do Backend thực thi từ dữ liệu CSDL chuẩn 3NF/BCNF; AI chỉ giải thích, gợi ý phân tầng và nhận xét theo tiêu chí.

---

## 3. Hướng dẫn cài đặt và chạy dự án

### Bước 1: Chuẩn bị Cơ sở dữ liệu (MySQL 8.4+)
- Tạo mới CSDL từ đầu: chạy `xianglingo_schema.sql`.
- Hoặc nâng cấp CSDL đang có sẵn dữ liệu: chạy `backend/scripts/2026_11_23_nang_cap_nghiep_vu_bo_sung.sql`.

### Bước 2: Chạy Backend
```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env   # Điền thông tin kết nối MySQL và OPENAI_API_KEY (nếu dùng AI)
uvicorn app.main:app --reload --port 8000
```

### Bước 3: Chạy Frontend
```powershell
cd frontend
npm install
Copy-Item .env.example .env.local
npm run dev
```
