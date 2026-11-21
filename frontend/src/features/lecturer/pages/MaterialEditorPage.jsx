import { useEffect, useRef, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";

import { useAuth } from "../../auth/context/AuthContext.jsx";
import Icon from "../../../shared/components/Icon.jsx";
import {
  createMaterial, deleteMaterial, getMaterial, materialAction, updateMaterial, uploadMaterialFile,
} from "../api/lecturerApi.js";
import MaterialViewer from "../components/MaterialViewer.jsx";
import StatusBadge from "../components/StatusBadge.jsx";
import { FILE_TYPE_LABELS, SKILL_LABELS, formatSize } from "../utils/labels.js";
import { useLevels } from "../utils/useLevels.js";
import "../styles/lecturer.css";

const blank = { ten: "", mo_ta: "", nguon: "", cap_do_id: "", ky_nang: "", duong_dan: "", file: null };

export default function MaterialEditorPage() {
  const { id } = useParams();
  const isNew = !id;
  const { token } = useAuth();
  const navigate = useNavigate();
  const levels = useLevels();
  const [form, setForm] = useState(blank);
  const [meta, setMeta] = useState(null);
  const [loading, setLoading] = useState(!isNew);
  const [busy, setBusy] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [showPreview, setShowPreview] = useState(false);
  const fileRef = useRef(null);

  function apply(data) {
    setMeta(data);
    setForm({ ten: data.ten, mo_ta: data.mo_ta || "", nguon: data.nguon || "", cap_do_id: data.cap_do_id || "",
      ky_nang: data.ky_nang || "", duong_dan: data.duong_dan, file: { loai_tep: data.loai_tep, kich_thuoc: data.kich_thuoc } });
  }

  useEffect(() => {
    if (isNew) { setForm(blank); setMeta(null); return undefined; }
    const controller = new AbortController();
    setLoading(true);
    getMaterial(token, id, controller.signal).then(apply)
      .catch((err) => err?.name !== "AbortError" && setError(err?.message || "Không tải được tài liệu"))
      .finally(() => setLoading(false));
    return () => controller.abort();
  }, [id, isNew, token]);

  async function pickFile(event) {
    const file = event.target.files?.[0];
    event.target.value = "";
    if (!file) return;
    if (file.size > 20 * 1024 * 1024) { setError("Tệp vượt quá 20 MB"); return; }
    setUploading(true);
    setError("");
    try {
      const data = await uploadMaterialFile(token, file);
      setForm((f) => ({ ...f, duong_dan: data.duong_dan, file: { loai_tep: data.loai_tep, kich_thuoc: data.kich_thuoc, ten: file.name } }));
      setShowPreview(false);
    } catch (err) {
      setError(err?.message || "Tải tệp thất bại");
    } finally {
      setUploading(false);
    }
  }

  async function run(action, after) {
    setBusy(true);
    setError("");
    setNotice("");
    try {
      const res = await action();
      await after?.(res);
      if (res?.message) setNotice(res.message);
    } catch (err) {
      setError(err?.message || "Thao tác thất bại");
    } finally {
      setBusy(false);
    }
  }

  function save(event) {
    event.preventDefault();
    if (!form.duong_dan) { setError("Chọn tệp tài liệu"); return; }
    const body = {
      ten: form.ten.trim(), mo_ta: form.mo_ta.trim() || null, nguon: form.nguon.trim() || null,
      cap_do_id: form.cap_do_id ? Number(form.cap_do_id) : null, ky_nang: form.ky_nang || null, duong_dan: form.duong_dan,
    };
    run(() => (isNew ? createMaterial(token, body) : updateMaterial(token, id, body)), async (res) => {
      if (String(res.id) !== String(id)) navigate(`/giang-vien/hoc-lieu/${res.id}`, { replace: isNew });
      else apply(await getMaterial(token, id));
    });
  }

  if (loading) return <p className="lv-muted">Đang tải…</p>;
  if (!isNew && !meta) return <p role="alert" className="lv-alert">{error || "Không tìm thấy tài liệu"}</p>;

  const status = meta?.trang_thai;
  const isLatest = !meta || meta.phien_ban === meta.phien_ban_moi_nhat;
  const fileChanged = meta && form.duong_dan !== meta.duong_dan;

  return (
    <section className="lv-page">
      <Link to="/giang-vien/hoc-lieu" className="lv-back"><Icon name="back" size={18} /> Tài liệu ôn tập</Link>
      <div className="lv-page__head">
        <div className="lv-page__intro">
          <h1>{isNew ? "Thêm tài liệu" : meta.ten}</h1>
          <p>{meta ? `Bản ${meta.phien_ban} · dùng trong ${meta.so_bai} bài` : "Nhập thông tin và chọn tệp PDF, ảnh hoặc audio."}</p>
        </div>
        {meta && <span className="lv-head-meta"><StatusBadge status={status} /></span>}
      </div>
      {meta && status !== "nhap" && isLatest && (
        <p className="lv-hint">Tài liệu đã {status === "da_dang" ? "đăng" : "ẩn"}. Lưu thay đổi sẽ tạo <strong>phiên bản nháp mới</strong>; tệp cũ không bị ghi đè.</p>
      )}
      {meta && !isLatest && <p className="lv-hint">Đây là phiên bản cũ, chỉ để xem.</p>}

      <form className="lv-card lv-form" onSubmit={save}>
        <fieldset disabled={busy || !isLatest} className="lv-plain">
          <div><label htmlFor="m-ten">Tên tài liệu</label><input id="m-ten" required maxLength={150} value={form.ten} onChange={(e) => setForm({ ...form, ten: e.target.value })} /></div>
          <div><label htmlFor="m-mota">Mô tả</label><textarea id="m-mota" rows={3} maxLength={3000} value={form.mo_ta} onChange={(e) => setForm({ ...form, mo_ta: e.target.value })} /></div>
          <div className="lv-grid-3">
            <div><label htmlFor="m-nguon">Nguồn</label><input id="m-nguon" maxLength={255} value={form.nguon} onChange={(e) => setForm({ ...form, nguon: e.target.value })} /></div>
            <div>
              <label htmlFor="m-cap">Cấp</label>
              <select id="m-cap" value={form.cap_do_id} onChange={(e) => setForm({ ...form, cap_do_id: e.target.value })}>
                <option value="">Không gắn cấp</option>
                {levels.map((l) => <option key={l.ma_cap_do} value={l.ma_cap_do}>{l.ten_cap_do}</option>)}
              </select>
            </div>
            <div>
              <label htmlFor="m-kn">Kỹ năng</label>
              <select id="m-kn" value={form.ky_nang} onChange={(e) => setForm({ ...form, ky_nang: e.target.value })}>
                <option value="">Không gắn kỹ năng</option>
                {Object.entries(SKILL_LABELS).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
              </select>
            </div>
          </div>
          <div className="lv-media">
            <span className="lv-media__label">Tệp (PDF, PNG, JPG, MP3, WAV · tối đa 20 MB)</span>
            {form.file && <span>{form.file.ten || FILE_TYPE_LABELS[form.file.loai_tep]} · {formatSize(form.file.kich_thuoc)}{fileChanged && " · tệp mới"}</span>}
            <div className="lv-media__actions">
              <button type="button" className="xbtn xbtn--ghost xbtn--sm" onClick={() => fileRef.current?.click()} disabled={uploading}>
                {uploading ? "Đang tải…" : form.duong_dan ? "Thay tệp" : "Chọn tệp"}
              </button>
            </div>
            <input ref={fileRef} type="file" hidden accept=".pdf,.png,.jpg,.jpeg,.mp3,.wav" onChange={pickFile} />
          </div>
        </fieldset>
        {error && <p role="alert" className="lv-alert">{error}</p>}
        {notice && <p role="status" className="lv-notice">{notice}</p>}
        {isLatest && (
          <div className="lv-actions">
            <button type="submit" className="xbtn" disabled={busy || uploading}>{status && status !== "nhap" ? "Lưu thành bản nháp mới" : "Lưu nháp"}</button>
            {status === "nhap" && <button type="button" className="xbtn xbtn--ghost" disabled={busy} onClick={() => run(() => materialAction(token, id, "dang"), async () => apply(await getMaterial(token, id)))}>Đăng cho học viên</button>}
            {status === "da_dang" && <button type="button" className="xbtn xbtn--ghost" disabled={busy} onClick={() => run(() => materialAction(token, id, "an"), async () => apply(await getMaterial(token, id)))}>Ẩn khỏi học viên</button>}
            {status === "da_an" && <button type="button" className="xbtn xbtn--ghost" disabled={busy} onClick={() => run(() => materialAction(token, id, "hien"), async () => apply(await getMaterial(token, id)))}>Hiện lại</button>}
            {status === "nhap" && !meta.so_bai && <button type="button" className="xbtn xbtn--danger" disabled={busy}
              onClick={() => window.confirm("Xóa tài liệu nháp này?") && run(() => deleteMaterial(token, id), () => navigate("/giang-vien/hoc-lieu"))}>Xoá</button>}
          </div>
        )}
      </form>

      {meta && !fileChanged && (
        <div className="lv-card">
          <div className="lv-actions">
            <h2>Xem như học viên</h2>
            <button type="button" className="xbtn xbtn--ghost xbtn--sm" onClick={() => setShowPreview((v) => !v)}>{showPreview ? "Đóng" : "Mở tệp"}</button>
          </div>
          {showPreview && <MaterialViewer id={meta.id} type={meta.loai_tep} title={meta.ten} />}
        </div>
      )}
    </section>
  );
}
