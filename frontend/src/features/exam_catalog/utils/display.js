// Chữ số Hán và lớp màu cho từng cấp; kỹ năng theo cấu trúc đề HSK 2.0 (Viết từ HSK 3)
export const ZH_NUM = ["", "一", "二", "三", "四"];
export const levelClass = (n) => `lv-c${n}`;
export const levelSkills = (n) => (n >= 3 ? "Nghe · Đọc · Viết" : "Nghe · Đọc");

export function examSkills(exam) {
  return [exam.so_nghe > 0 && "Nghe", exam.so_doc > 0 && "Đọc", exam.so_viet > 0 && "Viết"].filter(Boolean).join(" · ");
}
