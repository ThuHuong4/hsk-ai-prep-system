import { useState } from "react";

import { useAuth } from "../../auth/context/AuthContext.jsx";
import Icon from "../../../shared/components/Icon.jsx";
import { useRequest } from "../../../shared/api/useRequest.js";
import { createLevel, deleteLevel, levelAction, listLevelsAdmin, updateLevel } from "../api/lecturerApi.js";
import StatusBadge from "../components/StatusBadge.jsx";
import "../styles/lecturer.css";

const blank = { ma: "", ten: "", thu_tu: "", diem_toi_da_thi: "300", diem_dat_thi: "180" };

export default function LevelsPage() {
  const { token } = useAuth();
  const [reloadKey, setReloadKey] = useState(0);
  const { data, error, loading } = useRequest((signal) => listLevelsAdmin(token, signal), [token, reloadKey]);
  const [form, setForm] = useState(null); // null = đóng; { id?, ...fields }
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState({ type: "", text: "" });

  async function run(action) {
    setBusy(true);
    setMessage({ type: "", text: "" });
    try {
      const res = await action();
      setMessage({ type: "ok", text: res.message });
      setReloadKey((k) => k + 1);
      return true;
    } catch (err) {
      setMessage({ type: "bad", text: err?.message || "Thao tác thất bại" });
      return false;
    } finally {
      setBusy(false);
    }
  }

  async function save(event) {
    event.preventDefault();
    const body = {
      ma: form.ma.trim(), ten: form.ten.trim(), thu_tu: Number(form.thu_tu),
      diem_toi_da_thi: Number(form.diem_toi_da_thi), diem_dat_thi: Number(form.diem_dat_thi),
    };
    const ok = await run(() => (form.id ? updateLevel(token, form.id, body) : createLevel(token, body)));
    if (ok) setForm(null);
  }

  function openNew() {
    const next = (data?.reduce((m, l) => Math.max(m, l.thu_tu), 0) ?? 0) + 1;
    setForm({ ...blank, thu_tu: String(next) });
  }

  return (
    <section className="lv-page">
      <div className="lv-page__head">
        <div className="lv-page__intro">
          <h1>Cấp độ</h1>
          <p>Cấp mới dùng được cho Ôn luyện, Từ vựng, Thi thử sau khi đăng. Tổng điểm tối đa và mốc đạt dùng để chấm Thi thử.</p>
        </div>
        <button type="button" className="xbtn" onClick={openNew}><Icon name="plus" /> Thêm cấp</button>
      </div>

      {message.text && <p role={message.type === "ok" ? "status" : "alert"} className={message.type === "ok" ? "lv-notice" : "lv-alert"}>{message.text}</p>}
      {error && <p role="alert" className="lv-alert">{error}</p>}

      {form && (
        <form className="lv-card lv-form" onSubmit={save}>
          <h2>{form.id ? `Sửa ${form.ten || "cấp"}` : "Thêm cấp mới"}</h2>
          <div className="lv-grid-3">
            <div><label htmlFor="lv-ma">Mã cấp</label><input id="lv-ma" required maxLength={10} placeholder="VD: HSK5" value={form.ma} onChange={(e) => setForm({ ...form, ma: e.target.value })} /></div>
            <div><label htmlFor="lv-ten">Tên hiển thị</label><input id="lv-ten" required maxLength={50} placeholder="VD: HSK 5" value={form.ten} onChange={(e) => setForm({ ...form, ten: e.target.value })} /></div>
            <div><label htmlFor="lv-tt">Thứ tự</label><input id="lv-tt" type="number" min="1" max="99" required value={form.thu_tu} onChange={(e) => setForm({ ...form, thu_tu: e.target.value })} /></div>
            <div><label htmlFor="lv-max">Tổng điểm tối đa Thi thử</label><input id="lv-max" type="number" min="1" max="1000" required value={form.diem_toi_da_thi} onChange={(e) => setForm({ ...form, diem_toi_da_thi: e.target.value })} /></div>
            <div><label htmlFor="lv-pass">Mốc đạt</label><input id="lv-pass" type="number" min="1" max="1000" required value={form.diem_dat_thi} onChange={(e) => setForm({ ...form, diem_dat_thi: e.target.value })} /></div>
          </div>
          <div className="lv-actions">
            <button type="submit" className="xbtn" disabled={busy}>{busy ? "Đang lưu…" : "Lưu"}</button>
            <button type="button" className="xbtn xbtn--ghost" onClick={() => setForm(null)} disabled={busy}>Hủy</button>
          </div>
        </form>
      )}

      <div className="lv-table">
        <div className="lv-tr lv-tr--head lv-l-grid" aria-hidden="true">
          <span>Cấp</span><span>Thứ tự</span><span>Điểm Thi thử</span><span>Nội dung</span><span>Trạng thái</span><span />
        </div>
        {loading && <p className="lv-empty">Đang tải…</p>}
        {data?.map((l) => (
          <div className="lv-tr lv-l-grid" key={l.id}>
            <div className="lv-cell-main">
              <span className="lv-cell-icon"><Icon name="layers" /></span>
              <span className="lv-cell-text"><span className="lv-cell-title">{l.ten}</span><span className="lv-cell-sub">{l.ma}</span></span>
            </div>
            <span><span className="lv-cell-label">Thứ tự</span>{l.thu_tu}</span>
            <span><span className="lv-cell-label">Điểm</span>Đạt {l.diem_dat_thi}/{l.diem_toi_da_thi}</span>
            <span className="lv-cell-sub">{l.so_cau_hoi} câu · {l.so_bo_de} đề/bài · {l.so_tu_vung} từ · {l.so_tai_lieu} tài liệu</span>
            <span><StatusBadge status={l.trang_thai} /></span>
            <div className="lv-row-actions">
              <button type="button" className="xbtn xbtn--ghost xbtn--sm" disabled={busy}
                onClick={() => setForm({ id: l.id, ma: l.ma, ten: l.ten, thu_tu: String(l.thu_tu), diem_toi_da_thi: String(l.diem_toi_da_thi), diem_dat_thi: String(l.diem_dat_thi) })}>Sửa</button>
              {l.trang_thai === "nhap" && <button type="button" className="xbtn xbtn--sm" disabled={busy} onClick={() => run(() => levelAction(token, l.id, "dang"))}>Đăng</button>}
              {l.trang_thai === "da_dang" && <button type="button" className="xbtn xbtn--ghost xbtn--sm" disabled={busy} onClick={() => run(() => levelAction(token, l.id, "an"))}>Ẩn</button>}
              {l.trang_thai === "da_an" && <button type="button" className="xbtn xbtn--sm" disabled={busy} onClick={() => run(() => levelAction(token, l.id, "hien"))}>Hiện lại</button>}
              {l.trang_thai === "nhap" && <button type="button" className="xbtn xbtn--danger xbtn--sm" disabled={busy}
                onClick={() => window.confirm(`Xóa cấp ${l.ten}?`) && run(() => deleteLevel(token, l.id))}>Xoá</button>}
            </div>
          </div>
        ))}
      </div>
    </section>
  );
}
