import { useState } from "react";
import { Link } from "react-router-dom";

import { useAuth } from "../../auth/context/AuthContext.jsx";
import { aiDraftQuestions, createQuestion } from "../api/lecturerApi.js";
import QuestionPreview from "./QuestionPreview.jsx";
import { DANG_LABELS, SKILL_LABELS } from "../utils/labels.js";

const AI_TYPES = ["chon_mot", "dung_sai", "sap_xep", "dien_chu", "viet_mo", "dich_cau"];

/**
 * Giảng viên dùng AI soạn bản nháp (Mục 11):
 * nhập yêu cầu -> AI tạo bản nháp -> hệ thống báo thiếu/sai thành phần -> Giảng viên mở để sửa hoặc lưu nháp.
 * Không có nút đăng ở đây: câu chỉ được dùng sau khi Giảng viên mở ra kiểm tra và bấm Đăng (= duyệt).
 */
export default function AiDraftPanel({ levels, defaults, onUseDraft }) {
  const { token } = useAuth();
  const [req, setReq] = useState({
    cap_do_id: defaults.cap_do_id || levels[0]?.ma_cap_do || "",
    ky_nang: defaults.ky_nang || "doc",
    dang: AI_TYPES.includes(defaults.dang) ? defaults.dang : "chon_mot",
    chu_de: "",
    yeu_cau: "",
    so_luong: 3,
  });
  const [drafts, setDrafts] = useState([]);
  const [savedIds, setSavedIds] = useState({});
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  const set = (patch) => setReq((r) => ({ ...r, ...patch }));

  async function generate(e) {
    e.preventDefault();
    setBusy(true);
    setError("");
    setDrafts([]);
    setSavedIds({});
    try {
      const data = await aiDraftQuestions(token, {
        ...req,
        cap_do_id: Number(req.cap_do_id),
        so_luong: Number(req.so_luong),
        yeu_cau: req.yeu_cau.trim() || null,
      });
      setDrafts(data.ban_nhap || []);
    } catch (err) {
      setError(err?.message || "AI chưa soạn được, vui lòng thử lại");
    } finally {
      setBusy(false);
    }
  }

  async function saveDraft(index) {
    setBusy(true);
    setError("");
    try {
      const data = await createQuestion(token, drafts[index].cau_hoi);
      setSavedIds((m) => ({ ...m, [index]: data.id }));
    } catch (err) {
      setError(`Bản nháp ${index + 1}: ${err?.message || "không lưu được"}`);
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="lv-card lv-ai" aria-labelledby="ai-draft-title">
      <h2 id="ai-draft-title" className="lv-ai__title">Soạn nháp với AI</h2>
      <p className="lv-help">
        AI chỉ tạo bản nháp. Bạn kiểm tra, sửa rồi mới bấm Đăng. Câu lưu từ đây được ghi nguồn “Soạn với AI”.
      </p>

      <form className="lv-ai__form" onSubmit={generate}>
        <fieldset disabled={busy}>
          <div className="lv-grid-3">
            <div className="lv-field">
              <label htmlFor="ai-level">Cấp độ</label>
              <select id="ai-level" value={req.cap_do_id} onChange={(e) => set({ cap_do_id: e.target.value })}>
                {levels.map((l) => <option key={l.ma_cap_do} value={l.ma_cap_do}>{l.ten_cap_do}</option>)}
              </select>
            </div>
            <div className="lv-field">
              <label htmlFor="ai-skill">Kỹ năng</label>
              <select id="ai-skill" value={req.ky_nang} onChange={(e) => set({ ky_nang: e.target.value })}>
                {Object.entries(SKILL_LABELS).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
              </select>
            </div>
            <div className="lv-field">
              <label htmlFor="ai-type">Dạng câu</label>
              <select id="ai-type" value={req.dang} onChange={(e) => set({ dang: e.target.value })}>
                {AI_TYPES.map((t) => <option key={t} value={t}>{DANG_LABELS[t]}</option>)}
              </select>
            </div>
          </div>
          <div className="lv-ai__row">
            <div className="lv-field">
              <label htmlFor="ai-topic">Chủ đề</label>
              <input id="ai-topic" required minLength={2} maxLength={200} placeholder="Ví dụ: hẹn giờ gặp bạn, phủ định 不/没"
                value={req.chu_de} onChange={(e) => set({ chu_de: e.target.value })} />
            </div>
            <div className="lv-field lv-ai__count">
              <label htmlFor="ai-count">Số câu</label>
              <select id="ai-count" value={req.so_luong} onChange={(e) => set({ so_luong: e.target.value })}>
                {[1, 2, 3, 4, 5].map((n) => <option key={n} value={n}>{n}</option>)}
              </select>
            </div>
          </div>
          <div className="lv-field">
            <label htmlFor="ai-extra">Yêu cầu thêm (không bắt buộc)</label>
            <textarea id="ai-extra" rows={2} maxLength={1000} placeholder="Ví dụ: dùng từ 已经, câu ngắn dưới 12 chữ"
              value={req.yeu_cau} onChange={(e) => set({ yeu_cau: e.target.value })} />
          </div>
          <button type="submit" className="xbtn">{busy ? "AI đang soạn…" : "Soạn nháp"}</button>
        </fieldset>
      </form>

      {error && <p role="alert" className="lv-alert">{error}</p>}

      {drafts.length > 0 && (
        <ol className="lv-ai__list">
          {drafts.map((d, i) => (
            <li key={i} className="lv-ai__item">
              <QuestionPreview q={d.cau_hoi} number={i + 1} />
              {d.loi && <p className="lv-alert">Chưa đủ thành phần: {d.loi}. Mở để sửa trước khi lưu.</p>}
              {d.canh_bao?.map((w) => <p key={w} className="lv-hint">{w}</p>)}
              <div className="lv-actions">
                <button type="button" className="xbtn xbtn--ghost xbtn--sm" onClick={() => onUseDraft(d.cau_hoi)} disabled={busy}>
                  Mở để sửa
                </button>
                {savedIds[i] ? (
                  <Link className="xlink" to={`/giang-vien/cau-hoi/${savedIds[i]}`}>Đã lưu nháp · Mở câu #{savedIds[i]}</Link>
                ) : (
                  <button type="button" className="xbtn xbtn--sm" onClick={() => saveDraft(i)} disabled={busy || Boolean(d.loi)}
                    title={d.loi ? "Bản nháp còn thiếu thành phần, hãy mở để sửa" : undefined}>
                    Lưu thành nháp
                  </button>
                )}
              </div>
            </li>
          ))}
        </ol>
      )}
    </section>
  );
}
