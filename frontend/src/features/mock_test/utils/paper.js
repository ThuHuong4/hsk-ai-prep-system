import { splitOption } from "../../../shared/utils/format.js";

export { splitOption };

// Gom câu theo kỹ năng → phần → khối (câu lẻ hoặc nhóm cùng ngữ liệu), đánh số như đề giấy
const SECTION_ZH = { nghe: "听力", doc: "阅读", viet: "书写", tu_vung: "词汇" };
const SECTION_VI = { nghe: "Nghe", doc: "Đọc", viet: "Viết", tu_vung: "Từ vựng" };
const ZH_NUM = ["一", "二", "三", "四", "五", "六", "七", "八", "九"];

export const LETTERS = "ABCDEFGHIJKL";

export function buildPaper(items) {
  const sections = [];
  for (const item of items) {
    let section = sections[sections.length - 1];
    if (!section || section.ky_nang !== item.ky_nang) {
      section = { ky_nang: item.ky_nang, title: `${ZH_NUM[sections.length]}、${SECTION_ZH[item.ky_nang] ?? ""}`, label: SECTION_VI[item.ky_nang], parts: [] };
      sections.push(section);
    }
    let part = section.parts[section.parts.length - 1];
    if (!part || part.phan !== item.phan) {
      part = { phan: item.phan, title: `第${ZH_NUM[section.parts.length]}部分`, blocks: [], from: null, to: null };
      section.parts.push(part);
    }
    if (item.so_cau) {
      part.from = part.from ?? item.so_cau;
      part.to = item.so_cau;
    }
    const last = part.blocks[part.blocks.length - 1];
    if (item.cau_cha_id && last && last.group === item.cau_cha_id) last.items.push(item);
    else part.blocks.push({ group: item.cau_cha_id || null, items: [item] });
  }
  return sections;
}

export function formatClock(seconds) {
  const s = Math.max(0, Math.floor(seconds));
  const m = Math.floor(s / 60);
  return `${String(m).padStart(2, "0")}:${String(s % 60).padStart(2, "0")}`;
}
