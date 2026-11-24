// Tiện ích cho trang Soạn đề với AI theo từng phần.
// "Thẻ" = một mục AI soạn (câu đơn hoặc cụm), dạng { key, muc, loi, van_de_ai, luu_y, trung_lap, so_cau, da_kiem_tra, duyet }.

let seq = 0;
export const newKey = () => `t${Date.now().toString(36)}${(seq++).toString(36)}`;

export const LETTERS = "ABCDEFGH";

// Danh sách ô tệp cần tạo của một mục: đường dẫn tới trường + loại + nội dung để tạo
export function mediaSlots(muc) {
  const slots = [];
  if ("tep_hinh" in muc) slots.push({ path: ["tep_hinh"], loai: "hinh", nguon: muc.mo_ta_hinh, ten: "Hình của câu" });
  if ("tep_audio" in muc) slots.push({ path: ["tep_audio"], loai: "audio", nguon: muc.loi_nghe, ten: "Âm thanh" });
  (muc.lua_chon || []).forEach((o, i) => {
    if ("tep_hinh" in o) slots.push({ path: ["lua_chon", i, "tep_hinh"], loai: "hinh", nguon: o.mo_ta_hinh, ten: `Hình ${LETTERS[i]}` });
  });
  (muc.cau || []).forEach((c, i) => {
    if ("tep_audio" in c) slots.push({ path: ["cau", i, "tep_audio"], loai: "audio", nguon: c.loi_nghe, ten: `Âm thanh câu ${i + 1}` });
  });
  return slots;
}

export const slotId = (path) => path.join(".");

export function getAt(obj, path) {
  return path.reduce((o, k) => (o == null ? o : o[k]), obj);
}

// Gán bất biến (trả bản sao mới)
export function setAt(obj, path, value) {
  if (!path.length) return value;
  const [head, ...rest] = path;
  const copy = Array.isArray(obj) ? [...obj] : { ...obj };
  copy[head] = setAt(obj?.[head], rest, value);
  return copy;
}

export const missingMedia = (muc) => mediaSlots(muc).filter((s) => !getAt(muc, s.path));

export function summary(muc) {
  const bits = [muc.noi_dung, muc.loi_nghe, ...(muc.cau || []).slice(0, 2).map((c) => c.noi_dung || c.loi_nghe)];
  return bits.filter(Boolean).join(" / ").slice(0, 150);
}

// Có thể tích "đã kiểm tra": đủ tệp và không lỗi thiếu thành phần
export const canCheck = (card) => !card.loi && missingMedia(card.muc).length === 0;

const STORE = "xianglingo-ai-de-v1";

export function loadDraft(capDoId) {
  try {
    const all = JSON.parse(localStorage.getItem(STORE) || "{}");
    return all[capDoId] || null;
  } catch {
    return null;
  }
}

export function saveDraft(capDoId, data) {
  try {
    const all = JSON.parse(localStorage.getItem(STORE) || "{}");
    all[capDoId] = data;
    localStorage.setItem(STORE, JSON.stringify(all));
  } catch {
    /* trình duyệt chặn lưu: vẫn làm việc bình thường, chỉ không giữ khi tải lại trang */
  }
}

export function clearDraft(capDoId) {
  try {
    const all = JSON.parse(localStorage.getItem(STORE) || "{}");
    delete all[capDoId];
    localStorage.setItem(STORE, JSON.stringify(all));
  } catch {
    /* bỏ qua */
  }
}

// Chạy danh sách việc với tối đa `limit` việc cùng lúc
export async function runPool(tasks, limit = 3) {
  let next = 0;
  const workers = Array.from({ length: Math.min(limit, tasks.length) }, async () => {
    while (next < tasks.length) {
      const task = tasks[next++];
      await task();
    }
  });
  await Promise.all(workers);
}
