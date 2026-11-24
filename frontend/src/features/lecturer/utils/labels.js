import { formatDateTime, formatSize, mediaUrl } from "../../../shared/utils/format.js";

export { formatDateTime, formatSize, mediaUrl };

export const DANG_LABELS = {
  ngu_lieu: "Ngữ liệu chung (nhiều câu con)",
  chon_mot: "Chọn một đáp án",
  dung_sai: "Đúng / Sai",
  chon_bo_chung: "Chọn từ bộ phương án chung",
  sap_xep: "Sắp xếp thành câu",
  dien_chu: "Điền chữ",
  viet_mo: "Viết mở (AI chấm)",
  dich_cau: "Dịch câu (AI chấm)",
};
export const TOP_TYPES = ["chon_mot", "dung_sai", "ngu_lieu", "sap_xep", "dien_chu", "viet_mo", "dich_cau"];
export const CHILD_TYPES = ["chon_mot", "dung_sai", "chon_bo_chung", "sap_xep", "dien_chu", "viet_mo", "dich_cau"];

export const SOURCE_LABELS = { tu_soan: "Tự soạn", soan_voi_ai: "Soạn với AI", nguon_duoc_phep: "Nguồn được phép dùng" };
export const SKILL_LABELS = { nghe: "Nghe", doc: "Đọc", viet: "Viết", tu_vung: "Từ vựng" };
export const STATUS_LABELS = { nhap: "Nháp", da_dang: "Đang đăng", da_an: "Đã ẩn" };

export function optionLetter(index) {
  return String.fromCharCode(65 + index);
}

export const WORD_STATUS_LABELS = { nhap: "Nháp", xuat_ban: "Đã xuất bản", ngung_xuat_ban: "Ngừng xuất bản" };
export const FILE_TYPE_LABELS = { pdf: "PDF", png: "Ảnh", jpg: "Ảnh", mp3: "Âm thanh", wav: "Âm thanh" };
export const LESSON_SLOTS = [1, 2, 3, 4, 5];
export const slotName = (viTri) => (viTri === 5 ? "Kiểm tra cuối thửa" : `Bài ${viTri}`);
