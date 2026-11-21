export const ROLE_NAME = { 1: "Học viên", 2: "Quản trị viên", 3: "Giảng viên" };
export const ACTION_NAME = { khoa: "Khóa", mo_khoa: "Mở khóa", doi_vai_tro: "Đổi vai trò", tao_tai_khoan: "Tạo tài khoản" };
export const fmtTime = (iso) => (iso ? new Date(iso).toLocaleString("vi-VN", { dateStyle: "short", timeStyle: "short" }) : "—");

export function logText(row) {
  if (row.hanh_dong === "doi_vai_tro") return `${row.vai_tro_cu} → ${row.vai_tro_moi}`;
  if (row.hanh_dong === "tao_tai_khoan") return "Tạo mới · Giảng viên";
  return row.hanh_dong === "khoa" ? "Hoạt động → Khóa" : "Khóa → Hoạt động";
}
