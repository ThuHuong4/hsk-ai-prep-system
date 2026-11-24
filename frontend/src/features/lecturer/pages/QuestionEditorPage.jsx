import { useEffect, useMemo, useState } from "react";
import { Link, useLocation, useNavigate, useParams } from "react-router-dom";

import { useAuth } from "../../auth/context/AuthContext.jsx";
import {
  createQuestion, deleteQuestion, getQuestion, questionAction, updateQuestion,
  checkSimilar,
} from "../api/lecturerApi.js";
import Icon from "../../../shared/components/Icon.jsx";
import OptionsEditor from "../components/OptionsEditor.jsx";
import QuestionFields from "../components/QuestionFields.jsx";
import WordPicker from "../components/WordPicker.jsx";
import QuestionPreview, { SharedPassage } from "../components/QuestionPreview.jsx";
import StatusBadge from "../components/StatusBadge.jsx";
import { CHILD_TYPES, DANG_LABELS, SKILL_LABELS, SOURCE_LABELS, TOP_TYPES } from "../utils/labels.js";
import { answerDefaults, blankChild, blankQuestion, fromApi, toApi } from "../utils/questionForm.js";
import { useKnowledgeGroups } from "../hooks/useKnowledgeGroups.js";
import { useLevels } from "../hooks/useLevels.js";
import "../styles/lecturer.css";

export default function QuestionEditorPage() {
  const { id } = useParams();
  const isNew = !id;
  const { token } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const levels = useLevels();
  const groups = useKnowledgeGroups();
  // Bản nháp AI chuyển sang từ trang "Soạn câu với AI" (nút Sửa tay)
  const aiDraft = isNew ? location.state?.draft : null;

  const [form, setForm] = useState(() => blankQuestion());
  const [meta, setMeta] = useState(null); // dữ liệu đã lưu: trạng thái, phiên bản, đề đang dùng
  const [saved, setSaved] = useState(null); // payload đã lưu để biết có thay đổi chưa
  const [loading, setLoading] = useState(!isNew);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");

  useEffect(() => {
    if (isNew) {
      setForm(aiDraft ? fromApi(aiDraft) : blankQuestion(levels[0]?.ma_cap_do ?? ""));
      if (aiDraft) setNotice("Bản nháp AI đã nạp vào form. Kiểm tra, sửa rồi bấm Lưu nháp; bấm Đăng là duyệt.");
      setMeta(null);
      setSaved(null);
      return undefined;
    }
    const controller = new AbortController();
    setLoading(true);
    setError("");
    getQuestion(token, id, controller.signal)
      .then((data) => {
        const next = fromApi(data);
        setForm(next);
        setSaved(JSON.stringify(toApi(next)));
        setMeta(data);
      })
      .catch((err) => { if (err?.name !== "AbortError") setError(err?.message || "Không tải được câu hỏi"); })
      .finally(() => setLoading(false));
    return () => controller.abort();
  }, [id, isNew, token]); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    if (isNew && !form.cap_do_id && levels.length) setForm((f) => ({ ...f, cap_do_id: levels[0].ma_cap_do }));
  }, [levels, isNew, form.cap_do_id]);

  const payload = useMemo(() => toApi(form), [form]);
  const dirty = isNew || JSON.stringify(payload) !== saved;
  const status = meta?.trang_thai;
  const isLatest = !meta || meta.phien_ban === meta.phien_ban_moi_nhat;

  function set(patch) {
    setForm((f) => ({ ...f, ...patch }));
    setNotice("");
  }

  function changeType(dang) {
    const patch = { dang, ...answerDefaults(dang) };
    if (dang === "ngu_lieu") patch.cau_con = form.cau_con.length ? form.cau_con : [blankChild()];
    set(patch);
  }

  function updateChild(index, child) {
    set({ cau_con: form.cau_con.map((c, i) => (i === index ? child : c)) });
  }

  function changeChildType(index, dang) {
    updateChild(index, { ...form.cau_con[index], dang, ...answerDefaults(dang) });
  }

  async function run(action, after) {
    setBusy(true);
    setError("");
    setNotice("");
    try {
      const data = await action();
      await after?.(data);
      if (data?.message) setNotice(data.message);
    } catch (err) {
      setError(err?.message || "Thao tác thất bại");
    } finally {
      setBusy(false);
    }
  }

  async function reload(targetId) {
    const data = await getQuestion(token, targetId);
    const next = fromApi(data);
    setForm(next);
    setSaved(JSON.stringify(toApi(next)));
    setMeta(data);
  }

  async function handleSave() {
    // Câu đơn: cảnh báo nếu gần trùng câu đã có trong ngân hàng (không chặn, Giảng viên tự quyết)
    if (form.dang !== "ngu_lieu" && payload.noi_dung && payload.cap_do_id) {
      try {
        const res = await checkSimilar(token, {
          noi_dung: payload.noi_dung, cap_do_id: Number(payload.cap_do_id), dang: payload.dang,
          bo_qua_ma_goc: isNew ? null : meta?.ma_goc_id ?? null,
        });
        const hit = res.trung_lap?.[0];
        if (hit && !window.confirm(`Câu này giống ${Math.round(hit.do_giong * 100)}% câu #${hit.ma_goc_id} đã có:\n"${hit.noi_dung}"\n\nVẫn lưu?`)) return;
      } catch {
        // không kiểm tra được thì vẫn cho lưu
      }
    }
    run(
      () => (isNew ? createQuestion(token, payload) : updateQuestion(token, id, payload)),
      async (data) => {
        if (String(data.id) !== String(id)) navigate(`/giang-vien/cau-hoi/${data.id}`, { replace: isNew });
        else await reload(id);
      },
    );
  }

  function handleAction(action) {
    run(() => questionAction(token, id, action), () => reload(id));
  }

  function handleDelete() {
    if (!window.confirm("Xóa bản nháp này? Không hoàn tác được.")) return;
    run(() => deleteQuestion(token, id), () => navigate("/giang-vien/cau-hoi"));
  }

  if (loading) return <p className="lv-muted">Đang tải…</p>;
  if (!isNew && !meta) return <p role="alert">{error || "Không tìm thấy câu hỏi"}</p>;

  const sharedCount = form.dang === "ngu_lieu" ? form.phuong_an.length : 0;
  const readOnlyHint = !isLatest;

  return (
    <section className="lv-page">
      <Link to="/giang-vien/cau-hoi" className="lv-back"><Icon name="back" size={18} /> Ngân hàng câu hỏi</Link>
      <div className="lv-page__head">
        <div className="lv-page__intro">
          <h1>{isNew ? "Thêm câu hỏi" : `Câu hỏi #${meta.ma_goc_id}`}</h1>
          <p>Chọn dạng câu, nhập nội dung và đáp án. Khung bên phải là bản xem trước kèm đáp án.</p>
        </div>
        {meta && (
          <span className="lv-head-meta">
            <StatusBadge status={status} /> Bản {meta.phien_ban}
            {!isLatest && <> · <Link to={`/giang-vien/cau-hoi/${meta.cac_phien_ban[0].id}`}>Mở bản mới nhất</Link></>}
          </span>
        )}
      </div>

      {meta && status !== "nhap" && isLatest && (
        <p className="lv-hint">
          Câu này đã {status === "da_dang" ? "đăng" : "ẩn"}. Khi bấm Lưu, hệ thống tạo <strong>phiên bản nháp mới</strong>;
          bản cũ vẫn dùng cho học viên đến khi bạn đăng bản mới.
        </p>
      )}
      {readOnlyHint && <p className="lv-hint">Đây là phiên bản cũ, chỉ để xem.</p>}
      {meta?.de_dang_dung?.length > 0 && (
        <p className="lv-hint">Đang nằm trong đề: {meta.de_dang_dung.map((e) => `${e.ten} (bản ${e.phien_ban})`).join(", ")}</p>
      )}

      <div className="lv-editor">
        <div className="lv-editor__form">
          <fieldset className="lv-card" disabled={busy || readOnlyHint}>
            <legend>Phân loại</legend>
            <div className="lv-grid-3">
              <div className="lv-field">
                <label htmlFor="q-level">Cấp độ</label>
                <select id="q-level" value={form.cap_do_id} onChange={(e) => set({ cap_do_id: e.target.value })}>
                  {levels.map((l) => <option key={l.ma_cap_do} value={l.ma_cap_do}>{l.ten_cap_do}</option>)}
                </select>
              </div>
              <div className="lv-field">
                <label htmlFor="q-skill">Kỹ năng</label>
                <select id="q-skill" value={form.ky_nang} onChange={(e) => set({ ky_nang: e.target.value })}>
                  {Object.entries(SKILL_LABELS).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
                </select>
              </div>
              <div className="lv-field">
                <label htmlFor="q-type">Dạng câu</label>
                <select id="q-type" value={form.dang} onChange={(e) => changeType(e.target.value)}>
                  {TOP_TYPES.map((t) => <option key={t} value={t}>{DANG_LABELS[t]}</option>)}
                </select>
              </div>
            </div>
            <div className="lv-field">
              <label htmlFor="q-source">Nguồn nội dung</label>
              <select id="q-source" value={form.nguon_noi_dung || ""} onChange={(e) => set({ nguon_noi_dung: e.target.value })}>
                <option value="">Chưa xác định</option>
                {Object.entries(SOURCE_LABELS).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
              </select>
            </div>
            {form.dang !== "ngu_lieu" && (
              <div className="lv-field">
                <label htmlFor="q-group">Nhóm kiến thức (dùng cho cá nhân hóa)</label>
                <select id="q-group" value={form.nhom_kien_thuc_id ?? ""}
                  onChange={(e) => set({ nhom_kien_thuc_id: e.target.value ? Number(e.target.value) : null })}>
                  <option value="">Chưa gắn</option>
                  {groups.map((g) => <option key={g.id} value={g.id}>{g.ten}</option>)}
                </select>
              </div>
            )}
            {form.ky_nang === "tu_vung" && (
              <WordPicker capDoId={form.cap_do_id} value={form.tu_vung_id} word={form.tu_vung}
                onChange={(id, word) => set({ tu_vung_id: id, tu_vung: word })} />
            )}
            <div className="lv-checks">
              <label><input type="checkbox" checked={form.dung_thi_thu} onChange={(e) => set({ dung_thi_thu: e.target.checked })} /> Dùng cho Thi thử</label>
              <label><input type="checkbox" checked={form.dung_on_luyen} onChange={(e) => set({ dung_on_luyen: e.target.checked })} /> Dùng cho Ôn luyện</label>
              <label><input type="checkbox" checked={form.dung_dau_vao} onChange={(e) => set({ dung_dau_vao: e.target.checked })} /> Dùng cho đánh giá đầu vào</label>
            </div>
          </fieldset>

          <fieldset className="lv-card" disabled={busy || readOnlyHint}>
            <legend>{form.dang === "ngu_lieu" ? "Ngữ liệu chung" : "Nội dung và đáp án"}</legend>
            {form.dang === "ngu_lieu" ? (
              <>
                <QuestionFields q={{ ...form, dang: "ngu_lieu" }} idPrefix="q" onChange={(next) => set(next)} disabled={busy} />
                <OptionsEditor name="q-shared" mode="plain" title="Bộ phương án chung (cho câu con dạng “chọn từ bộ chung”, có thể bỏ trống)"
                  options={form.phuong_an} onChange={(v) => set({ phuong_an: v })} disabled={busy} />
              </>
            ) : (
              <QuestionFields q={form} idPrefix="q" onChange={(next) => set(next)} disabled={busy} />
            )}
          </fieldset>

          {form.dang === "ngu_lieu" && (
            <fieldset className="lv-card" disabled={busy || readOnlyHint}>
              <legend>Câu con ({form.cau_con.length})</legend>
              {form.cau_con.map((child, index) => (
                <div className="lv-child" key={child.key}>
                  <div className="lv-child__head">
                    <strong>Câu con {index + 1}</strong>
                    <select aria-label={`Dạng câu con ${index + 1}`} value={child.dang} onChange={(e) => changeChildType(index, e.target.value)}>
                      {CHILD_TYPES.map((t) => <option key={t} value={t}>{DANG_LABELS[t]}</option>)}
                    </select>
                    {form.cau_con.length > 1 && (
                      <button type="button" className="xlink xlink--danger" onClick={() => set({ cau_con: form.cau_con.filter((_, i) => i !== index) })}>Xóa</button>
                    )}
                  </div>
                  <QuestionFields q={child} idPrefix={`c${index}`} sharedCount={sharedCount} capDoId={form.cap_do_id}
                    onChange={(next) => updateChild(index, next)} disabled={busy} />
                </div>
              ))}
              {form.cau_con.length < 30 && (
                <button type="button" className="xbtn xbtn--ghost xbtn--sm" onClick={() => set({ cau_con: [...form.cau_con, blankChild(sharedCount >= 2 ? "chon_bo_chung" : "chon_mot")] })}>
                  + Thêm câu con
                </button>
              )}
              <small className="lv-help">Thứ tự câu trong đề do phần Đề thi thử quyết định.</small>
            </fieldset>
          )}

          {error && <p role="alert" className="lv-alert">{error}</p>}
          {notice && <p role="status" className="lv-notice">{notice}</p>}

          {!readOnlyHint && (
            <div className="lv-actions">
              <button type="button" className="xbtn" onClick={handleSave} disabled={busy || !dirty}>
                {busy ? "Đang xử lý…" : status && status !== "nhap" ? "Lưu thành bản nháp mới" : "Lưu nháp"}
              </button>
              {status === "nhap" && (
                <button type="button" className="xbtn xbtn--ghost" onClick={() => handleAction("dang")} disabled={busy || dirty}
                  title={dirty ? "Lưu thay đổi trước khi đăng" : undefined}>
                  Đăng
                </button>
              )}
              {status === "da_dang" && <button type="button" className="xbtn xbtn--ghost" onClick={() => handleAction("an")} disabled={busy}>Ẩn</button>}
              {status === "da_an" && <button type="button" className="xbtn xbtn--ghost" onClick={() => handleAction("hien")} disabled={busy}>Hiện lại</button>}
              {status === "nhap" && <button type="button" className="xbtn xbtn--danger" onClick={handleDelete} disabled={busy}>Xóa nháp</button>}
              {dirty && !isNew && <span className="lv-dirty">Có thay đổi chưa lưu</span>}
            </div>
          )}
        </div>

        <aside className="lv-editor__preview" aria-label="Xem trước">
          <h2>Xem trước</h2>
          {form.dang === "ngu_lieu" ? (
            <>
              <SharedPassage q={payload} />
              {payload.cau_con.map((c, i) => <QuestionPreview key={i} q={c} number={i + 1} />)}
            </>
          ) : (
            <QuestionPreview q={payload} />
          )}
        </aside>
      </div>
    </section>
  );
}
