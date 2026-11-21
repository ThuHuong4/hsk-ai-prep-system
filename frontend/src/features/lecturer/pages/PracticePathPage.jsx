import { useEffect, useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";

import { useAuth } from "../../auth/context/AuthContext.jsx";
import Icon from "../../../shared/components/Icon.jsx";
import { useRequest } from "../../../shared/api/useRequest.js";
import { createLand, createLesson, deleteLand, getPath, landAction, moveLand, updateLand } from "../api/lecturerApi.js";
import StatusBadge from "../components/StatusBadge.jsx";
import { LESSON_SLOTS, SKILL_LABELS, slotName } from "../utils/labels.js";
import { useLevels } from "../utils/useLevels.js";
import "../styles/lecturer.css";

export default function PracticePathPage() {
  const { token } = useAuth();
  const levels = useLevels();
  const navigate = useNavigate();
  const [params, setParams] = useSearchParams();
  const skill = params.get("ky_nang") || "nghe";
  const level = params.get("cap_do_id") || "";
  const [reloadKey, setReloadKey] = useState(0);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState({ type: "", text: "" });
  const [landForm, setLandForm] = useState(null); // { id?, ten, muc_tieu }

  useEffect(() => {
    if (!level && levels.length) setParams({ ky_nang: skill, cap_do_id: String(levels[0].ma_cap_do) }, { replace: true });
  }, [level, levels, skill, setParams]);

  const { data, error, loading } = useRequest(
    level ? (signal) => getPath(token, { cap_do_id: level, ky_nang: skill }, signal) : null,
    [token, level, skill, reloadKey],
  );

  async function run(action, after) {
    setBusy(true);
    setMessage({ type: "", text: "" });
    try {
      const res = await action();
      setMessage({ type: "ok", text: res.message });
      setReloadKey((k) => k + 1);
      after?.(res);
    } catch (err) {
      setMessage({ type: "bad", text: err?.message || "Thao tác thất bại" });
    } finally {
      setBusy(false);
    }
  }

  function saveLand(event) {
    event.preventDefault();
    const body = { ten: landForm.ten.trim(), muc_tieu: landForm.muc_tieu.trim() || null };
    run(() => (landForm.id ? updateLand(token, landForm.id, body)
      : createLand(token, { ...body, cap_do_id: Number(level), ky_nang: skill })), () => setLandForm(null));
  }

  function addLesson(land, viTri) {
    const ten = window.prompt(`Tên ${slotName(viTri).toLowerCase()} cho thửa "${land.ten}"`, viTri === 5 ? `Kiểm tra cuối thửa: ${land.ten}` : "");
    if (!ten || !ten.trim()) return;
    run(() => createLesson(token, { thua_id: land.id, vi_tri: viTri, ten: ten.trim() }), (res) => navigate(`/giang-vien/bai-luyen/bai/${res.id}`));
  }

  return (
    <section className="lv-page">
      <div className="lv-page__head">
        <div className="lv-page__intro">
          <h1>Bài ôn luyện</h1>
          <p>Lộ trình Kỹ năng → Cấp → Thửa → 5 ô: bài 1–4 (≥ 5 câu, đúng 5/5) và kiểm tra cuối thửa (≥ 10 câu đáp án xác định, đúng 10/10).</p>
        </div>
        <button type="button" className="xbtn" disabled={!level} onClick={() => setLandForm({ ten: "", muc_tieu: "" })}><Icon name="plus" /> Thêm thửa</button>
      </div>

      <div className="lv-filters">
        <div className="lv-seg" role="tablist" aria-label="Kỹ năng">
          {Object.entries(SKILL_LABELS).map(([k, v]) => (
            <button key={k} type="button" role="tab" aria-selected={skill === k} className={skill === k ? "is-active" : undefined}
              onClick={() => setParams({ ky_nang: k, cap_do_id: level })}>{v}</button>
          ))}
        </div>
        <select aria-label="Cấp độ" value={level} onChange={(e) => setParams({ ky_nang: skill, cap_do_id: e.target.value })}>
          {levels.map((l) => <option key={l.ma_cap_do} value={l.ma_cap_do}>{l.ten_cap_do}</option>)}
        </select>
      </div>
      {skill === "viet" && <p className="lv-help">Viết bắt đầu từ HSK 3 (Viết không có HSK 1–2).</p>}

      {message.text && <p role={message.type === "ok" ? "status" : "alert"} className={message.type === "ok" ? "lv-notice" : "lv-alert"}>{message.text}</p>}
      {error && <p role="alert" className="lv-alert">{error}</p>}

      {landForm && (
        <form className="lv-card lv-form" onSubmit={saveLand}>
          <h2>{landForm.id ? "Sửa thửa" : `Thêm thửa – ${SKILL_LABELS[skill]}`}</h2>
          <div><label htmlFor="land-ten">Tên thửa (chủ đề)</label><input id="land-ten" required maxLength={150} value={landForm.ten} onChange={(e) => setLandForm({ ...landForm, ten: e.target.value })} /></div>
          <div><label htmlFor="land-mt">Mục tiêu</label><textarea id="land-mt" rows={2} maxLength={2000} value={landForm.muc_tieu} onChange={(e) => setLandForm({ ...landForm, muc_tieu: e.target.value })} /></div>
          <div className="lv-actions">
            <button type="submit" className="xbtn" disabled={busy}>Lưu</button>
            <button type="button" className="xbtn xbtn--ghost" onClick={() => setLandForm(null)}>Hủy</button>
          </div>
        </form>
      )}

      {loading && <p className="lv-muted">Đang tải…</p>}
      {data && data.thua.length === 0 && <p className="lv-card lv-muted">Chưa có thửa nào cho {SKILL_LABELS[skill]} ở cấp này. Bấm “Thêm thửa” để bắt đầu.</p>}

      <ol className="lv-lands">
        {data?.thua.map((land, index) => (
          <li key={land.id} className="lv-card lv-land">
            <div className="lv-land__head">
              <span className="lv-item__no">{index + 1}</span>
              <div className="lv-cell-text">
                <span className="lv-cell-title">{land.ten}</span>
                <span className="lv-cell-sub">{land.muc_tieu || "Chưa có mục tiêu"}{land.phien_ban > 1 && ` · bản ${land.phien_ban}`}</span>
              </div>
              <StatusBadge status={land.trang_thai} />
              <div className="lv-land__actions">
                <button type="button" className="xlink" aria-label="Đưa thửa lên" disabled={busy || index === 0} onClick={() => run(() => moveLand(token, land.id, "len"))}><Icon name="up" size={18} /></button>
                <button type="button" className="xlink" aria-label="Đưa thửa xuống" disabled={busy || index === data.thua.length - 1} onClick={() => run(() => moveLand(token, land.id, "xuong"))}><Icon name="down" size={18} /></button>
                <button type="button" className="xbtn xbtn--ghost xbtn--sm" disabled={busy} onClick={() => setLandForm({ id: land.id, ten: land.ten, muc_tieu: land.muc_tieu || "" })}>Sửa</button>
                {land.trang_thai === "nhap" && <button type="button" className="xbtn xbtn--sm" disabled={busy} onClick={() => run(() => landAction(token, land.id, "dang"))}>Đăng</button>}
                {land.trang_thai === "da_dang" && <button type="button" className="xbtn xbtn--ghost xbtn--sm" disabled={busy} onClick={() => run(() => landAction(token, land.id, "an"))}>Ẩn</button>}
                {land.trang_thai === "da_an" && <button type="button" className="xbtn xbtn--sm" disabled={busy} onClick={() => run(() => landAction(token, land.id, "hien"))}>Hiện lại</button>}
                {land.trang_thai === "nhap" && land.bai.length === 0 && (
                  <button type="button" className="xbtn xbtn--danger xbtn--sm" disabled={busy}
                    onClick={() => window.confirm(`Xóa thửa "${land.ten}"?`) && run(() => deleteLand(token, land.id))}>Xoá</button>
                )}
              </div>
            </div>
            <ul className="lv-slots">
              {LESSON_SLOTS.map((viTri) => {
                const lesson = land.bai.find((b) => b.vi_tri === viTri);
                return (
                  <li key={viTri} className={`lv-slot${viTri === 5 ? " lv-slot--final" : ""}`}>
                    <span className="lv-slot__name">{slotName(viTri)}</span>
                    {lesson ? (
                      <Link to={`/giang-vien/bai-luyen/bai/${lesson.id}`} className="lv-slot__body">
                        <span className="lv-slot__title">{lesson.ten}</span>
                        <span className={lesson.so_cau < lesson.can_toi_thieu ? "lv-slot__count is-short" : "lv-slot__count"}>
                          {lesson.so_cau}/{lesson.can_toi_thieu} câu{lesson.ten_tai_lieu && " · có tài liệu"}
                        </span>
                        <StatusBadge status={lesson.trang_thai} />
                      </Link>
                    ) : (
                      <button type="button" className="lv-slot__body lv-slot__empty" disabled={busy} onClick={() => addLesson(land, viTri)}>
                        <Icon name="plus" size={18} /> Tạo {viTri === 5 ? "bài kiểm tra" : "bài"}
                      </button>
                    )}
                  </li>
                );
              })}
            </ul>
          </li>
        ))}
      </ol>
    </section>
  );
}
