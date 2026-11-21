export const DANG_LABELS = {
  ngu_lieu: "Ngữ liệu chung (nhiều câu con)",
  chon_mot: "Chọn một đáp án",
  dung_sai: "Đúng / Sai",
  chon_bo_chung: "Chọn từ bộ phương án chung",
  sap_xep: "Sắp xếp thành câu",
  dien_chu: "Điền chữ",
  viet_mo: "Viết mở (AI chấm)",
};
export const TOP_TYPES = ["chon_mot", "dung_sai", "ngu_lieu", "sap_xep", "dien_chu", "viet_mo"];
export const CHILD_TYPES = ["chon_mot", "dung_sai", "chon_bo_chung", "sap_xep", "dien_chu", "viet_mo"];

export const SKILL_LABELS = { nghe: "Nghe", doc: "Đọc", viet: "Viết", tu_vung: "Từ vựng" };
export const STATUS_LABELS = { nhap: "Nháp", da_dang: "Đang đăng", da_an: "Đã ẩn" };

export function mediaUrl(path) {
  if (!path) return null;
  if (/^https?:\/\//i.test(path) || path.startsWith("/")) return path;
  return `/media/${path}`;
}

export function optionLetter(index) {
  return String.fromCharCode(65 + index);
}

export const WORD_STATUS_LABELS = { nhap: "Nháp", xuat_ban: "Đã xuất bản", ngung_xuat_ban: "Ngừng xuất bản" };
export const FILE_TYPE_LABELS = { pdf: "PDF", png: "Ảnh", jpg: "Ảnh", mp3: "Âm thanh", wav: "Âm thanh" };
export const LESSON_SLOTS = [1, 2, 3, 4, 5];
export const slotName = (viTri) => (viTri === 5 ? "Kiểm tra cuối thửa" : `Bài ${viTri}`);

export function formatSize(bytes) {
  if (!bytes) return "";
  if (bytes < 1024 * 1024) return `${Math.max(1, Math.round(bytes / 1024))} KB`;
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`;
}

export function formatDateTime(value) {
  if (!value) return "";
  const d = new Date(value);
  return Number.isNaN(d.getTime()) ? String(value) : d.toLocaleString("vi-VN", { dateStyle: "short", timeStyle: "short" });
}
