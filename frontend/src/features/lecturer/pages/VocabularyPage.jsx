import { useMemo, useState } from "react";
import { useSearchParams } from "react-router-dom";

import { useAuth } from "../../auth/context/AuthContext.jsx";
import Icon from "../../../shared/components/Icon.jsx";
import { useRequest } from "../../../shared/api/useRequest.js";
import {
  createWord, deleteWord, importWords, listLevelsAdmin, listWords, updateWord, wordAction,
} from "../api/lecturerApi.js";
import MediaInput from "../components/MediaInput.jsx";
import StatusBadge from "../components/StatusBadge.jsx";
import { parseCsv, toCsv, downloadText } from "../utils/csv.js";
import { WORD_STATUS_LABELS } from "../utils/labels.js";
import "../styles/lecturer.css";
import CreatorTag from "../components/CreatorTag.jsx";

const PAGE_SIZE = 30;
const blank = { chu_han: "", pinyin: "", nghia: "", cap_do_id: "", vd_cau: "", vd_pinyin: "", vd_nghia: "", vd_audio: null };
const TEMPLATE_HEADER = ["chu_han", "pinyin", "nghia", "cap", "vd_cau", "vd_pinyin", "vd_nghia"];

const orNull = (v) => (v && String(v).trim() ? String(v).trim() : null);

export default function VocabularyPage() {
  const { token } = useAuth();
  const [params] = useSearchParams();
  const { data: levels } = useRequest((signal) => listLevelsAdmin(token, signal), [token]);
  const [filters, setFilters] = useState({ cap_do_id: "", trang_thai: params.get("trang_thai") || "", q: "" });
  const [search, setSearch] = useState("");
  const [page, setPage] = useState(1);
  const [reloadKey, setReloadKey] = useState(0);
  const { data, error, loading } = useRequest(
    (signal) => listWords(token, { ...filters, trang: page, so_dong: PAGE_SIZE }, signal),
    [token, JSON.stringify(filters), page, reloadKey],
  );
  const [form, setForm] = useState(null);
  const [importRows, setImportRows] = useState(null);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState({ type: "", text: "" });

  const levelByCode = useMemo(() => {
    const map = new Map();
    (levels || []).forEach((l) => { map.set(l.ma.toUpperCase(), l.id); map.set(l.ten.toUpperCase().replace(/\s+/g, ""), l.id); });
    return map;
  }, [levels]);

  async function run(action, after) {
    setBusy(true);
    setMessage({ type: "", text: "" });
    try {
      const res = await action();
      setMessage({ type: "ok", text: res.message });
      setReloadKey((k) => k + 1);
      after?.(res);
      return true;
    } catch (err) {
      setMessage({ type: "bad", text: err?.message || "Thao tác thất bại" });
      return false;
    } finally {
      setBusy(false);
    }
  }

  function setFilter(name, value) {
    setFilters((f) => ({ ...f, [name]: value }));
    setPage(1);
  }

  function save(event) {
    event.preventDefault();
    const body = {
      chu_han: form.chu_han.trim(), pinyin: form.pinyin.trim(), nghia: form.nghia.trim(), cap_do_id: Number(form.cap_do_id),
      vd_cau: orNull(form.vd_cau), vd_pinyin: orNull(form.vd_pinyin), vd_nghia: orNull(form.vd_nghia), vd_audio: form.vd_audio || null,
    };
    run(() => (form.id ? updateWord(token, form.id, body) : createWord(token, body)), () => setForm(null));
  }

  async function readImport(event) {
    const file = event.target.files?.[0];
    event.target.value = "";
    if (!file) return;
    const rows = parseCsv(await file.text());
    if (rows.length < 2) {
      setMessage({ type: "bad", text: "Tệp không có dòng dữ liệu (dòng đầu là tiêu đề)" });
      return;
    }
    const header = rows[0].map((h) => h.trim().toLowerCase());
    const col = (name) => header.indexOf(name);
    if (["chu_han", "pinyin", "nghia", "cap"].some((n) => col(n) < 0)) {
      setMessage({ type: "bad", text: "Tệp cần các cột: chu_han, pinyin, nghia, cap (xem tệp mẫu)" });
      return;
    }
    const words = [];
    const problems = [];
    rows.slice(1).forEach((r, i) => {
      const get = (n) => (col(n) >= 0 ? (r[col(n)] || "").trim() : "");
      const levelId = levelByCode.get(get("cap").toUpperCase().replace(/\s+/g, ""));
      if (!get("chu_han") || !get("pinyin") || !get("nghia") || !levelId) {
        problems.push(i + 2);
        return;
      }
      words.push({
        chu_han: get("chu_han"), pinyin: get("pinyin"), nghia: get("nghia"), cap_do_id: levelId,
        vd_cau: orNull(get("vd_cau")), vd_pinyin: orNull(get("vd_pinyin")), vd_nghia: orNull(get("vd_nghia")), vd_audio: null,
      });
    });
    setImportRows({ words, problems, name: file.name });
  }

  function downloadTemplate() {
    downloadText("mau_tu_vung.csv", toCsv([TEMPLATE_HEADER, ["你好", "nǐ hǎo", "xin chào", "HSK1", "你好，我是小明。", "nǐ hǎo, wǒ shì xiǎo míng.", "Xin chào, mình là Tiểu Minh."]]));
  }

  const total = data?.tong ?? 0;
  const pages = Math.max(1, Math.ceil(total / PAGE_SIZE));

  return (
    <section className="lv-page">
      <div className="lv-page__head">
        <div className="lv-page__intro">
          <h1>Từ vựng</h1>
          <p>Học viên chỉ thấy từ đã xuất bản. Từ ngừng xuất bản không vào lượt mới, lịch sử giữ nguyên.</p>
        </div>
        <div className="lv-actions">
          <label className="xbtn xbtn--ghost">
            <Icon name="doc" /> Nhập từ tệp CSV
            <input type="file" accept=".csv,text/csv" hidden onChange={readImport} />
          </label>
          <button type="button" className="xbtn" onClick={() => setForm({ ...blank, cap_do_id: levels?.[0]?.id ?? "" })}><Icon name="plus" /> Thêm từ</button>
        </div>
      </div>

      {message.text && <p role={message.type === "ok" ? "status" : "alert"} className={message.type === "ok" ? "lv-notice" : "lv-alert"}>{message.text}</p>}
      {error && <p role="alert" className="lv-alert">{error}</p>}

      {importRows && (
        <div className="lv-card">
          <h2>Nhập từ “{importRows.name}”</h2>
          <p>{importRows.words.length} từ hợp lệ sẽ được lưu ở trạng thái nháp. Từ trùng chữ Hán + pinyin với từ đã có sẽ được bỏ qua.</p>
          {importRows.problems.length > 0 && (
            <p className="lv-alert">Bỏ qua các dòng thiếu dữ liệu hoặc sai mã cấp: {importRows.problems.slice(0, 20).join(", ")}{importRows.problems.length > 20 ? "…" : ""}</p>
          )}
          <div className="lv-actions">
            <button type="button" className="xbtn" disabled={busy || importRows.words.length === 0}
              onClick={() => run(() => importWords(token, importRows.words), () => setImportRows(null))}>Nhập {importRows.words.length} từ</button>
            <button type="button" className="xbtn xbtn--ghost" onClick={() => setImportRows(null)}>Hủy</button>
          </div>
        </div>
      )}
      <p className="lv-help">
        Tệp CSV gồm các cột {TEMPLATE_HEADER.join(", ")}; cột cap ghi mã cấp (VD: HSK1).{" "}
        <button type="button" className="xlink" onClick={downloadTemplate}>Tải tệp mẫu</button>
      </p>

      {form && (
        <form className="lv-card lv-form" onSubmit={save}>
          <h2>{form.id ? `Sửa từ ${form.chu_han}` : "Thêm từ"}</h2>
          <div className="lv-grid-3">
            <div><label htmlFor="w-han">Chữ Hán</label><input id="w-han" className="zh" required maxLength={20} value={form.chu_han} onChange={(e) => setForm({ ...form, chu_han: e.target.value })} /></div>
            <div><label htmlFor="w-py">Pinyin</label><input id="w-py" required maxLength={60} value={form.pinyin} onChange={(e) => setForm({ ...form, pinyin: e.target.value })} /></div>
            <div>
              <label htmlFor="w-cap">Cấp</label>
              <select id="w-cap" required value={form.cap_do_id} onChange={(e) => setForm({ ...form, cap_do_id: e.target.value })}>
                {(levels || []).map((l) => <option key={l.id} value={l.id}>{l.ten}</option>)}
              </select>
            </div>
          </div>
          <div><label htmlFor="w-nghia">Nghĩa tiếng Việt</label><input id="w-nghia" required maxLength={255} value={form.nghia} onChange={(e) => setForm({ ...form, nghia: e.target.value })} /></div>
          <fieldset className="lv-options">
            <legend>Câu ví dụ (tùy chọn, tối đa 1)</legend>
            <div><label htmlFor="w-vd">Câu ví dụ</label><input id="w-vd" className="zh" maxLength={1000} value={form.vd_cau} onChange={(e) => setForm({ ...form, vd_cau: e.target.value })} /></div>
            <div className="lv-grid-3">
              <div><label htmlFor="w-vdpy">Pinyin ví dụ</label><input id="w-vdpy" maxLength={1000} value={form.vd_pinyin} onChange={(e) => setForm({ ...form, vd_pinyin: e.target.value })} /></div>
              <div><label htmlFor="w-vdn">Nghĩa ví dụ</label><input id="w-vdn" maxLength={1000} value={form.vd_nghia} onChange={(e) => setForm({ ...form, vd_nghia: e.target.value })} /></div>
              <MediaInput kind="audio" label="Audio ví dụ" value={form.vd_audio} onChange={(v) => setForm({ ...form, vd_audio: v })} disabled={busy} />
            </div>
          </fieldset>
          <div className="lv-actions">
            <button type="submit" className="xbtn" disabled={busy}>{busy ? "Đang lưu…" : "Lưu"}</button>
            <button type="button" className="xbtn xbtn--ghost" onClick={() => setForm(null)} disabled={busy}>Hủy</button>
          </div>
        </form>
      )}

      <div className="lv-filters">
        <form className="lv-searchbox" role="search" onSubmit={(e) => { e.preventDefault(); setFilter("q", search.trim()); }}>
          <Icon name="search" />
          <input type="search" placeholder="Tìm chữ Hán, pinyin hoặc nghĩa" value={search} onChange={(e) => setSearch(e.target.value)} aria-label="Tìm từ" />
        </form>
        <select aria-label="Cấp độ" value={filters.cap_do_id} onChange={(e) => setFilter("cap_do_id", e.target.value)}>
          <option value="">Mọi cấp</option>
          {(levels || []).map((l) => <option key={l.id} value={l.id}>{l.ten}</option>)}
        </select>
        <select aria-label="Trạng thái" value={filters.trang_thai} onChange={(e) => setFilter("trang_thai", e.target.value)}>
          <option value="">Mọi trạng thái</option>
          {Object.entries(WORD_STATUS_LABELS).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
        </select>
      </div>

      <div className="lv-table">
        <div className="lv-tr lv-tr--head lv-w-grid" aria-hidden="true">
          <span>Từ</span><span>Nghĩa</span><span>Cấp</span><span>Ví dụ</span><span>Trạng thái</span><span />
        </div>
        {loading && <p className="lv-empty">Đang tải…</p>}
        {!loading && data?.muc.length === 0 && <p className="lv-empty">Chưa có từ nào khớp bộ lọc.</p>}
        {!loading && data?.muc.map((w) => (
          <div className="lv-tr lv-w-grid" key={w.id}>
            <div className="lv-cell-text">
              <span className="lv-cell-title zh lv-word">{w.chu_han}</span>
              <span className="lv-cell-sub">{w.pinyin}{w.so_cau_hoi > 0 && ` · ${w.so_cau_hoi} câu hỏi`}</span>
              <CreatorTag creator={w.nguoi_tao} />
            </div>
            <span>{w.nghia}</span>
            <span><span className="lv-cell-label">Cấp</span>{w.ten_cap_do}</span>
            <span className="lv-cell-sub zh">{w.vd_cau || "—"}</span>
            <span><StatusBadge status={w.trang_thai} /></span>
            <div className="lv-row-actions">
              <button type="button" className="xbtn xbtn--ghost xbtn--sm" disabled={busy}
                onClick={() => setForm({ id: w.id, chu_han: w.chu_han, pinyin: w.pinyin, nghia: w.nghia, cap_do_id: w.cap_do_id, vd_cau: w.vd_cau || "", vd_pinyin: w.vd_pinyin || "", vd_nghia: w.vd_nghia || "", vd_audio: w.vd_audio })}>Sửa</button>
              {w.trang_thai !== "xuat_ban" && <button type="button" className="xbtn xbtn--sm" disabled={busy} onClick={() => run(() => wordAction(token, w.id, "xuat-ban"))}>Xuất bản</button>}
              {w.trang_thai === "xuat_ban" && <button type="button" className="xbtn xbtn--ghost xbtn--sm" disabled={busy} onClick={() => run(() => wordAction(token, w.id, "ngung"))}>Ngừng</button>}
              {w.trang_thai === "nhap" && <button type="button" className="xbtn xbtn--danger xbtn--sm" disabled={busy}
                onClick={() => window.confirm(`Xóa từ ${w.chu_han}?`) && run(() => deleteWord(token, w.id))}>Xoá</button>}
            </div>
          </div>
        ))}
      </div>

      {pages > 1 && (
        <nav className="lv-pager" aria-label="Phân trang">
          <button type="button" className="xbtn xbtn--ghost xbtn--sm" disabled={page <= 1} onClick={() => setPage((p) => p - 1)}>Trước</button>
          <span>Trang {page}/{pages} · {total} từ</span>
          <button type="button" className="xbtn xbtn--ghost xbtn--sm" disabled={page >= pages} onClick={() => setPage((p) => p + 1)}>Sau</button>
        </nav>
      )}
    </section>
  );
}
