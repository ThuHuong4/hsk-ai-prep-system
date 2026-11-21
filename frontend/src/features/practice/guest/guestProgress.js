// Tiến độ học thử của Khách: chỉ lưu trên trình duyệt này (localStorage), không lưu vào tài khoản.
// Năng lượng 5/ngày, sai hoặc bỏ qua −1; sang ngày mới hồi về 5.
const KEY = "xianglingo-guest-practice";
export const GUEST_MAX_ENERGY = 5;

const today = () => new Date().toLocaleDateString("en-CA");

function fresh() {
  return { ngay: today(), nang_luong: GUEST_MAX_ENERGY, dat: [], chua_dat: [] };
}

export function readGuest() {
  let state = fresh();
  try {
    const saved = JSON.parse(localStorage.getItem(KEY) || "null");
    if (saved && typeof saved === "object") {
      state = {
        ngay: saved.ngay,
        nang_luong: Number.isInteger(saved.nang_luong) ? Math.min(Math.max(saved.nang_luong, 0), GUEST_MAX_ENERGY) : GUEST_MAX_ENERGY,
        dat: Array.isArray(saved.dat) ? saved.dat.filter(Number.isInteger) : [],
        chua_dat: Array.isArray(saved.chua_dat) ? saved.chua_dat.filter(Number.isInteger) : [],
      };
    }
  } catch {
    // Trình duyệt chặn bộ nhớ: dùng trạng thái mới
  }
  if (state.ngay !== today()) state = { ...state, ngay: today(), nang_luong: GUEST_MAX_ENERGY };
  return state;
}

function write(state) {
  try { localStorage.setItem(KEY, JSON.stringify(state)); } catch { /* bỏ qua */ }
  return state;
}

export function spendEnergy() {
  const state = readGuest();
  const cut = state.nang_luong > 0 ? 1 : 0;
  write({ ...state, nang_luong: state.nang_luong - cut });
  return cut;
}

export function markResult(maGoc, passed) {
  const state = readGuest();
  const dat = new Set(state.dat);
  const fail = new Set(state.chua_dat);
  if (passed) { dat.add(maGoc); fail.delete(maGoc); } else if (!dat.has(maGoc)) fail.add(maGoc);
  return write({ ...state, dat: [...dat], chua_dat: [...fail] });
}

// Tính lại trạng thái ô theo đúng quy tắc mở khóa của Học viên (mục 4.1)
export function applyGuestProgress(lands, state) {
  const dat = new Set(state.dat);
  const fail = new Set(state.chua_dat);
  let openLand = true;
  return lands.map((land) => {
    let prevOk = openLand;
    const o = land.o.map((slot) => {
      if (slot.trang_thai === "chua_xuat_ban") { prevOk = false; return slot; }
      const passed = dat.has(slot.ma_goc_id);
      let trang_thai = "chua_hoc";
      if (passed) trang_thai = "da_xong";
      else if (!prevOk) trang_thai = "khoa";
      else if (fail.has(slot.ma_goc_id)) trang_thai = "chua_dat";
      prevOk = passed;
      return { ...slot, trang_thai };
    });
    const harvested = o.length === 5 && o[4].trang_thai === "da_xong";
    const result = { ...land, mo: openLand, thu_hoach: harvested, o };
    openLand = harvested;
    return result;
  });
}

export function nextLesson(lands) {
  for (const land of lands) {
    const slot = land.o.find((o) => o.trang_thai === "chua_dat" || o.trang_thai === "chua_hoc");
    if (slot) return { thua: land.ten, ...slot };
  }
  return null;
}
