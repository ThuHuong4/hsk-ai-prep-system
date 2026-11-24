export const STUDENT_MENU = [
  { to: "/hoc-vien", label: "Trang chủ", icon: "home", end: true, tab: true },
  { to: "/hoc-vien/on-luyen", label: "Lộ trình ôn", icon: "route", tab: true },
  { to: "/hoc-vien/so-tay-cau-sai", label: "Sổ tay", icon: "book", tab: true },
  { to: "/hoc-vien/thi-thu", label: "Thi thử", icon: "timer", tab: true },
  { to: "/hoc-vien/thong-ke", label: "Kết quả & Thống kê", icon: "chart" },
  { to: "/hoc-vien/tai-lieu", label: "Tài liệu", icon: "upload" },
  { to: "/hoc-vien/ca-nhan", label: "Cá nhân", icon: "user" },
];

export const LECTURER_MENU = [
  { to: "/giang-vien", label: "Tổng quan", icon: "home", end: true },
  { to: "/giang-vien/cap-do", label: "Cấp độ", icon: "layers" },
  { to: "/giang-vien/tu-vung", label: "Từ vựng", icon: "pen" },
  { to: "/giang-vien/hoc-lieu", label: "Tài liệu ôn tập", icon: "doc" },
  { to: "/giang-vien/cau-hoi", label: "Ngân hàng câu hỏi", icon: "spark" },
  { to: "/giang-vien/chat-luong", label: "Chất lượng câu hỏi", icon: "chart" },
  { to: "/giang-vien/bo-de", label: "Đề thi thử HSK", icon: "timer" },
  { to: "/giang-vien/bai-luyen", label: "Bài ôn luyện", icon: "route" },
  { to: "/giang-vien/cham-viet", label: "Chấm bài Viết", icon: "check", badge: "cham_sai_cho" },
  { to: "/giang-vien/bao-loi", label: "Báo lỗi nội dung", icon: "alert", badge: "bao_loi_moi" },
];

export const ADMIN_MENU = [
  { to: "/quan-tri", label: "Tổng quan", icon: "home", end: true },
  { to: "/quan-tri/tai-khoan", label: "Tài khoản", icon: "user" },
  { to: "/quan-tri/vai-tro", label: "Vai trò", icon: "layers" },
  { to: "/quan-tri/nhat-ky", label: "Nhật ký quản trị", icon: "doc" },
];
