// Dữ liệu form câu hỏi ↔ payload API
let keySeed = 0;
export const newKey = () => `k${Date.now()}_${keySeed++}`;

const TEXT_FIELDS = [
  "noi_dung", "tep_audio", "tep_hinh", "mo_ta_hinh", "loi_nghe", "pinyin", "dich_nghia",
  "goi_y", "goi_y_2", "giai_thich", "tu_bat_buoc", "tieu_chi_mo_ta",
];
// Dạng chấm theo tiêu chí (AI chấm): có điểm tối đa, ngưỡng đạt, tiêu chí chấm
export const SCORED_TYPES = ["viet_mo", "dich_cau"];

const emptyOption = () => ({ key: newKey(), noi_dung: "", tep_hinh: null, la_dap_an_dung: false });

export function answerDefaults(dang) {
  const base = { phuong_an: [], dap_an_chap_nhan: [], dap_an_thu_tu: null, diem_toi_da: "", nguong_dat: "", tu_bat_buoc: "", tieu_chi_mo_ta: "" };
  if (dang === "chon_mot") return { ...base, phuong_an: [emptyOption(), emptyOption(), emptyOption()] };
  if (dang === "dung_sai") {
    return {
      ...base,
      phuong_an: [
        { key: newKey(), noi_dung: "Đúng", tep_hinh: null, la_dap_an_dung: true },
        { key: newKey(), noi_dung: "Sai", tep_hinh: null, la_dap_an_dung: false },
      ],
    };
  }
  if (dang === "sap_xep") return { ...base, phuong_an: [emptyOption(), emptyOption(), emptyOption()], dap_an_chap_nhan: [""] };
  if (dang === "dien_chu") return { ...base, dap_an_chap_nhan: [""] };
  if (dang === "viet_mo") return { ...base, diem_toi_da: "10", nguong_dat: "6" };
  if (dang === "dich_cau") return { ...base, diem_toi_da: "10", nguong_dat: "6", dap_an_chap_nhan: [""] };
  return base;
}

export function blankChild(dang = "chon_mot") {
  return { key: newKey(), id: null, dang, ...Object.fromEntries(TEXT_FIELDS.map((f) => [f, ""])), ...answerDefaults(dang) };
}

export function blankQuestion(capDoId = "") {
  return {
    dang: "chon_mot",
    cap_do_id: capDoId,
    ky_nang: "nghe",
    dung_on_luyen: false,
    dung_thi_thu: true,
    dung_dau_vao: false,
    tu_vung_id: null,
    tu_vung: null,
    nguon_noi_dung: "tu_soan",
    nhom_kien_thuc_id: null,
    ...Object.fromEntries(TEXT_FIELDS.map((f) => [f, ""])),
    ...answerDefaults("chon_mot"),
    cau_con: [],
  };
}

// Câu từ API → state form
function fromApiPart(q) {
  return {
    ...Object.fromEntries(TEXT_FIELDS.map((f) => [f, q[f] ?? ""])),
    dang: q.dang,
    dap_an_thu_tu: q.dap_an_thu_tu ?? null,
    diem_toi_da: q.diem_toi_da != null ? String(q.diem_toi_da) : "",
    nguong_dat: q.nguong_dat != null ? String(q.nguong_dat) : "",
    phuong_an: (q.phuong_an || []).map((o) => ({ key: newKey(), noi_dung: o.noi_dung ?? "", tep_hinh: o.tep_hinh, la_dap_an_dung: o.la_dap_an_dung })),
    dap_an_chap_nhan: q.dap_an_chap_nhan?.length ? [...q.dap_an_chap_nhan] : [],
  };
}

export function fromApi(q) {
  return {
    ...fromApiPart(q),
    cap_do_id: q.cap_do_id,
    ky_nang: q.ky_nang,
    dung_on_luyen: q.dung_on_luyen,
    dung_thi_thu: q.dung_thi_thu,
    dung_dau_vao: q.dung_dau_vao,
    tu_vung_id: q.tu_vung_id ?? null,
    tu_vung: q.tu_vung ?? null,
    nguon_noi_dung: q.nguon_noi_dung ?? "",
    nhom_kien_thuc_id: q.nhom_kien_thuc_id ?? null,
    cau_con: (q.cau_con || []).map((c) => ({ key: newKey(), id: c.id, ...fromApiPart(c) })),
  };
}

const orNull = (v) => {
  if (v === null || v === undefined) return null;
  const t = String(v).trim();
  return t ? t : null;
};
const numOrNull = (v) => (orNull(v) === null ? null : Number(v));

function toApiPart(q) {
  const part = { dang: q.dang };
  TEXT_FIELDS.forEach((f) => { part[f] = orNull(q[f]); });
  part.dap_an_thu_tu = q.dang === "chon_bo_chung" ? numOrNull(q.dap_an_thu_tu) : null;
  const scored = SCORED_TYPES.includes(q.dang);
  part.diem_toi_da = scored ? numOrNull(q.diem_toi_da) : null;
  part.nguong_dat = scored ? numOrNull(q.nguong_dat) : null;
  if (q.dang !== "viet_mo") part.tu_bat_buoc = null;
  if (!scored) part.tieu_chi_mo_ta = null;
  part.phuong_an = (q.phuong_an || []).map((o) => ({
    noi_dung: orNull(o.noi_dung), tep_hinh: o.tep_hinh || null, la_dap_an_dung: Boolean(o.la_dap_an_dung),
  }));
  part.dap_an_chap_nhan = (q.dap_an_chap_nhan || []).map((a) => a.trim()).filter(Boolean);
  return part;
}

export function toApi(q) {
  return {
    ...toApiPart(q),
    cap_do_id: Number(q.cap_do_id),
    ky_nang: q.ky_nang,
    dung_on_luyen: q.dung_on_luyen,
    dung_thi_thu: q.dung_thi_thu,
    dung_dau_vao: q.dung_dau_vao,
    tu_vung_id: q.ky_nang === "tu_vung" ? q.tu_vung_id ?? null : null,
    nguon_noi_dung: q.nguon_noi_dung || null,
    nhom_kien_thuc_id: q.dang === "ngu_lieu" ? null : q.nhom_kien_thuc_id ?? null,
    cau_con: q.dang === "ngu_lieu" ? q.cau_con.map((c) => ({ id: c.id || null, ...toApiPart(c) })) : [],
  };
}
