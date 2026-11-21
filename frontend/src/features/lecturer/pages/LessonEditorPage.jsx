import { useCallback, useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";

import { useAuth } from "../../auth/context/AuthContext.jsx";
import Icon from "../../../shared/components/Icon.jsx";
import { useRequest } from "../../../shared/api/useRequest.js";
import {
  deleteLesson, getLesson, getQuestion, lessonAction, listMaterials, saveLessonItems, updateLesson,
} from "../api/lecturerApi.js";
import QuestionPicker from "../components/QuestionPicker.jsx";
import QuestionPreview, { SharedPassage } from "../components/QuestionPreview.jsx";
import StatusBadge from "../components/StatusBadge.jsx";
import { DANG_LABELS, SKILL_LABELS, slotName } from "../utils/labels.js";
import "../styles/lecturer.css";

export default function LessonEditorPage() {
  const { id } = useParams();
  const { token } = useAuth();
  const navigate = useNavigate();
  const [lesson, setLesson] = useState(null);
  const [info, setInfo] = useState({ ten: "", muc_tieu: "", tai_lieu_id: "" });
  const [items, setItems] = useState([]);
  const [saved, setSaved] = useState({ info: "", items: "" });
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");

  const apply = useCallback((data) => {
    const nextInfo = { ten: data.ten, muc_tieu: data.muc_tieu || "", tai_lieu_id: data.tai_lieu_id ? String(data.tai_lieu_id) : "" };
    const nextItems = data.cau_hoi.map((i) => ({ cau_hoi_id: i.cau_hoi_id, cau_cha_id: i.cau_cha_id, ky_nang: i.ky_nang, cau_hoi: i.cau_hoi }));
    setLesson(data);
    setInfo(nextInfo);
    setItems(nextItems);
    setSaved({ info: JSON.stringify(nextInfo), items: JSON.stringify(nextItems.map((i) => i.cau_hoi_id)) });
  }, []);

  useEffect(() => {
    const controller = new AbortController();
    setLoading(true);
    getLesson(token, id, controller.signal).then(apply)
      .catch((err) => err?.name !== "AbortError" && setError(err?.message || "Không tải được bài"))
      .finally(() => setLoading(false));
    return () => controller.abort();
  }, [id, token, apply]);

  const land = lesson?.thua;
  const { data: materials } = useRequest(
    land ? (signal) => listMaterials(token, { cap_do_id: land.cap_do_id }, signal) : null,
    [token, land?.cap_do_id],
  );

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

  const reload = () => getLesson(token, id).then(apply);

  async function addQuestion(row) {
    setError("");
    try {
      const detail = await getQuestion(token, row.id);
      const present = new Set(items.map((i) => i.cau_hoi_id));
      if (row.dang === "ngu_lieu") {
        const added = detail.cau_con.filter((c) => !present.has(c.id) && !(lesson.loai === "cuoi_thua" && c.dang === "viet_mo"))
          .map((c) => ({ cau_hoi_id: c.id, cau_cha_id: detail.id, ky_nang: row.ky_nang, cau_hoi: c }));
        setLesson((l) => ({ ...l, ngu_lieu: { ...l.ngu_lieu, [detail.id]: detail } }));
        setItems((list) => [...list, ...added]);
      } else if (!present.has(row.id)) {
        if (lesson.loai === "cuoi_thua" && row.dang === "viet_mo") {
          setError("Kiểm tra cuối thửa chỉ dùng câu có đáp án xác định");
          return;
        }
        setItems((list) => [...list, { cau_hoi_id: row.id, cau_cha_id: null, ky_nang: row.ky_nang, cau_hoi: detail }]);
      }
    } catch (err) {
      setError(err?.message || "Không thêm được câu");
    }
  }

  function moveItem(index, delta) {
    setItems((list) => {
      const next = [...list];
      const target = index + delta;
      if (target < 0 || target >= next.length) return list;
      [next[index], next[target]] = [next[target], next[index]];
      return next;
    });
  }

  if (loading) return <p className="lv-muted">Đang tải…</p>;
  if (!lesson) return <p role="alert" className="lv-alert">{error || "Không tìm thấy bài"}</p>;

  const status = lesson.trang_thai;
  const editable = status === "nhap";
  const isLatest = lesson.phien_ban === lesson.phien_ban_moi_nhat;
  const infoDirty = JSON.stringify(info) !== saved.info;
  const itemsDirty = JSON.stringify(items.map((i) => i.cau_hoi_id)) !== saved.items;
  const parents = lesson.ngu_lieu || {};
  const backTo = `/giang-vien/bai-luyen?ky_nang=${land.ky_nang}&cap_do_id=${land.cap_do_id}`;

  return (
    <section className="lv-page">
      <Link to={backTo} className="lv-back"><Icon name="back" size={18} /> Thửa “{land.ten}”</Link>
      <div className="lv-page__head">
        <div className="lv-page__intro">
          <h1>{lesson.ten}</h1>
          <p>{slotName(lesson.vi_tri)} · {SKILL_LABELS[land.ky_nang]} · cần ít nhất {lesson.can_toi_thieu} câu{lesson.loai === "cuoi_thua" && " có đáp án xác định"}</p>
        </div>
        <span className="lv-head-meta"><StatusBadge status={status} /> Bản {lesson.phien_ban}</span>
      </div>
      {!editable && isLatest && <p className="lv-hint">Bài đã {status === "da_dang" ? "đăng" : "ẩn"}. Bấm <strong>Tạo bản nháp để sửa</strong>; bản hiện tại vẫn dùng đến khi đăng bản mới.</p>}
      {!isLatest && <p className="lv-hint">Đây là phiên bản cũ, chỉ để xem.</p>}

      <fieldset className="lv-card" disabled={busy || !editable}>
        <legend>Thông tin bài</legend>
        <div><label htmlFor="ls-ten">Tên bài</label><input id="ls-ten" maxLength={150} value={info.ten} onChange={(e) => setInfo({ ...info, ten: e.target.value })} /></div>
        <div><label htmlFor="ls-mt">Mục tiêu</label><textarea id="ls-mt" rows={2} maxLength={2000} value={info.muc_tieu} onChange={(e) => setInfo({ ...info, muc_tieu: e.target.value })} /></div>
        <div>
          <label htmlFor="ls-tl">Tài liệu tham khảo (tối đa 1)</label>
          <select id="ls-tl" value={info.tai_lieu_id} onChange={(e) => setInfo({ ...info, tai_lieu_id: e.target.value })}>
            <option value="">Không gắn tài liệu</option>
            {(materials || []).filter((m) => m.trang_thai !== "da_an" || String(m.id) === info.tai_lieu_id).map((m) => (
              <option key={m.id} value={m.id}>{m.ten}{m.trang_thai === "nhap" ? " (nháp)" : ""}</option>
            ))}
          </select>
        </div>
        {editable && (
          <div className="lv-actions">
            <button type="button" className="xbtn" disabled={busy || !infoDirty || !info.ten.trim()}
              onClick={() => run(() => updateLesson(token, id, { ten: info.ten.trim(), muc_tieu: info.muc_tieu.trim() || null, tai_lieu_id: info.tai_lieu_id ? Number(info.tai_lieu_id) : null }), reload)}>Lưu thông tin</button>
          </div>
        )}
      </fieldset>

      <div className="lv-editor">
        <div className="lv-editor__form">
          <fieldset className="lv-card" disabled={busy || !editable}>
            <legend>Câu trong bài ({items.length}/{lesson.can_toi_thieu})</legend>
            {items.length === 0 && <p className="lv-muted">Chưa có câu nào. Thêm từ ngân hàng câu đã đăng bên dưới.</p>}
            <ol className="lv-items">
              {items.map((item, index) => (
                <li key={item.cau_hoi_id} className="lv-item">
                  <span className="lv-item__no">{index + 1}</span>
                  <span className="lv-item__text">
                    <span className="lv-cell-sub">#{item.cau_hoi.ma_goc_id} · {DANG_LABELS[item.cau_hoi.dang]}{item.cau_cha_id && " · thuộc ngữ liệu"}</span>
                    <span className="zh">{item.cau_hoi.noi_dung || "(âm thanh / hình)"}</span>
                  </span>
                  <span className="lv-item__ctrl">
                    <button type="button" className="xlink" aria-label="Lên" onClick={() => moveItem(index, -1)} disabled={index === 0}><Icon name="up" size={18} /></button>
                    <button type="button" className="xlink" aria-label="Xuống" onClick={() => moveItem(index, 1)} disabled={index === items.length - 1}><Icon name="down" size={18} /></button>
                    <button type="button" className="xlink xlink--danger" onClick={() => setItems((l) => l.filter((_, i) => i !== index))}>Gỡ</button>
                  </span>
                </li>
              ))}
            </ol>
            <p className="lv-help">Học viên làm bài sẽ được xáo thứ tự câu và phương án.</p>
            {editable && (
              <div className="lv-actions">
                <button type="button" className="xbtn" disabled={busy || !itemsDirty}
                  onClick={() => run(() => saveLessonItems(token, id, items.map((i) => ({ cau_hoi_id: i.cau_hoi_id }))), reload)}>Lưu danh sách câu</button>
                {itemsDirty && <span className="lv-dirty">Có thay đổi chưa lưu</span>}
              </div>
            )}
          </fieldset>

          {editable && (
            <QuestionPicker token={token} capDoId={land.cap_do_id} kyNang={land.ky_nang} purpose="on_luyen" chosen={items} onAdd={addQuestion}
              title={`Ngân hàng câu đã đăng (Ôn luyện · ${SKILL_LABELS[land.ky_nang]})`} />
          )}

          {error && <p role="alert" className="lv-alert">{error}</p>}
          {notice && <p role="status" className="lv-notice">{notice}</p>}

          {isLatest && (
            <div className="lv-actions">
              {status === "nhap" && <button type="button" className="xbtn" disabled={busy || infoDirty || itemsDirty} onClick={() => run(() => lessonAction(token, id, "dang"), reload)}>Đăng cho học viên</button>}
              {status !== "nhap" && <button type="button" className="xbtn" disabled={busy}
                onClick={() => run(() => lessonAction(token, id, "ban-nhap"), (res) => (String(res.id) !== String(id) ? navigate(`/giang-vien/bai-luyen/bai/${res.id}`) : reload()))}>Tạo bản nháp để sửa</button>}
              {status === "da_dang" && <button type="button" className="xbtn xbtn--ghost" disabled={busy} onClick={() => run(() => lessonAction(token, id, "an"), reload)}>Ẩn khỏi học viên</button>}
              {status === "da_an" && <button type="button" className="xbtn xbtn--ghost" disabled={busy} onClick={() => run(() => lessonAction(token, id, "hien"), reload)}>Hiện lại</button>}
              {status === "nhap" && <button type="button" className="xbtn xbtn--danger" disabled={busy}
                onClick={() => window.confirm("Xóa bài nháp này?") && run(() => deleteLesson(token, id), () => navigate(backTo))}>Xoá</button>}
            </div>
          )}
        </div>

        <aside className="lv-editor__preview" aria-label="Xem trước bài">
          <h2>Xem trước</h2>
          {items.map((item, index) => {
            const prev = items[index - 1];
            const showPassage = item.cau_cha_id && (!prev || prev.cau_cha_id !== item.cau_cha_id) && parents[item.cau_cha_id];
            return (
              <div key={item.cau_hoi_id}>
                {showPassage && <SharedPassage q={parents[item.cau_cha_id]} />}
                <QuestionPreview q={item.cau_hoi} number={index + 1} />
              </div>
            );
          })}
        </aside>
      </div>
    </section>
  );
}
