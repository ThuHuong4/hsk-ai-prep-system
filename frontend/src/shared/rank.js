// Danh hiệu theo tổng KN (mục 4.6: KN chỉ để tạo động lực, không mở khóa). Đổi mốc chỉ cần sửa bảng này.
export const RANKS = [
  { min: 0, ten: "Sơ học", zh: "初学" },
  { min: 200, ten: "Nhập môn", zh: "入门" },
  { min: 500, ten: "Chăm học", zh: "勤学" },
  { min: 1000, ten: "Tiến bộ", zh: "进步" },
  { min: 2000, ten: "Thuần thục", zh: "熟练" },
  { min: 3500, ten: "Tinh thông", zh: "精通" },
  { min: 5000, ten: "Đại sư", zh: "大师" },
];

export function rankOf(kn = 0) {
  let i = 0;
  RANKS.forEach((r, k) => { if (kn >= r.min) i = k; });
  const next = RANKS[i + 1] || null;
  const span = next ? next.min - RANKS[i].min : 1;
  return {
    bac: i + 1, ten: RANKS[i].ten, zh: RANKS[i].zh, next,
    con_thieu: next ? next.min - kn : 0,
    ti_le: next ? Math.min(1, (kn - RANKS[i].min) / span) : 1,
  };
}
