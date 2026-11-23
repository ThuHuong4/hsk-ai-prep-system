import { useCallback, useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";

import { useAuth } from "../../auth/context/AuthContext.jsx";
import {
  createExam, deleteExam, examAction, getExam, getQuestion, saveExamItems, updateExam,
} from "../api/lecturerApi.js";
import Icon from "../../../shared/components/Icon.jsx";
import MediaInput from "../components/MediaInput.jsx";
import QuestionPreview, { SharedPassage } from "../components/QuestionPreview.jsx";
import QuestionPicker from "../components/QuestionPicker.jsx";
import StatusBadge from "../components/StatusBadge.jsx";
import { DANG_LABELS, SKILL_LABELS } from "../utils/labels.js";
import { useLevels } from "../hooks/useLevels.js";
import "../styles/lecturer.css";

const DEFAULT_PART = { nghe: 1, doc: 2, viet: 3, tu_vung: 4 };
const blankInfo = (capDoId = "") => ({ cap_do_id: capDoId, ten: "", ma_de: "", nguon: "", thoi_luong_phut: "", tep_audio_chung: null });

function infoPayload(info) {
  return {
    cap_do_id: Number(info.cap_do_id),
    ten: info.ten.trim(),
    ma_de: info.ma_de.trim(),
    nguon: info.nguon.trim() || null,
    thoi_luong_phut: info.thoi_luong_phut ? Number(info.thoi_luong_phut) : null,
    tep_audio_chung: info.tep_audio_chung || null,
  };
}

function itemsPayload(items) {
  return items.map((i) => ({ cau_hoi_id: i.cau_hoi_id, phan: i.phan ? Number(i.phan) : null, la_cau_vi_du: i.la_cau_vi_du }));
}

export default function ExamEditorPage() {
  const { id } = useParams();
  const isNew = !id;
  const { token } = useAuth();
  const navigate = useNavigate();
  const levels = useLevels();

  const [exam, setExam] = useState(null);
  const [info, setInfo] = useState(blankInfo());
  const [items, setItems] = useState([]);
  const [savedInfo, setSavedInfo] = useState("");
  const [savedItems, setSavedItems] = useState("[]");
  const [loading, setLoading] = useState(!isNew);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");

  const apply = useCallback((data) => {
    const nextInfo = {
      cap_do_id: data.cap_do_id, ten: data.ten, ma_de: data.ma_de || "", nguon: data.nguon || "",
      thoi_luong_phut: data.thoi_luong_phut ? String(data.thoi_luong_phut) : "", tep_audio_chung: data.tep_audio_chung,
    };
    const nextItems = data.cau_hoi.map((i) => ({
      cau_hoi_id: i.cau_hoi_id, phan: i.phan, la_cau_vi_du: i.la_cau_vi_du, ky_nang: i.ky_nang,
      cau_cha_id: i.cau_cha_id, cau_hoi: i.cau_hoi,
    }));
    setExam(data);
    setInfo(nextInfo);
    setItems(nextItems);
    setSavedInfo(JSON.stringify(infoPayload(nextInfo)));
    setSavedItems(JSON.stringify(itemsPayload(nextItems)));
  }, []);

  useEffect(() => {
    if (isNew) {
      setExam(null);
      setInfo(blankInfo(levels[0]?.ma_cap_do ?? ""));
      setItems([]);
      return undefined;
    }
    const controller = new AbortController();
    setLoading(true);
    getExam(token, id, controller.signal)
      .then(apply)
      .catch((err) => { if (err?.name !== "AbortError") setError(err?.message || "Không tải được đề"); })
      .finally(() => setLoading(false));
    return () => controller.abort();
  }, [id, isNew, token, apply]); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    if (isNew && !info.cap_do_id && levels.length) setInfo((i) => ({ ...i, cap_do_id: levels[0].ma_cap_do }));
  }, [levels, isNew, info.cap_do_id]);

  const status = exam?.trang_thai;
  const editable = isNew || status === "nhap";
  const isLatest = !exam || exam.phien_ban === exam.phien_ban_moi_nhat;
  const infoDirty = isNew || JSON.stringify(infoPayload(info)) !== savedInfo;
  const itemsDirty = JSON.stringify(itemsPayload(items)) !== savedItems;
  const parents = exam?.ngu_lieu || {};

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

  const reload = (targetId = id) => getExam(token, targetId).then(apply);

  function saveInfo() {
    if (!info.ten.trim() || !info.ma_de.trim()) {
      setError("Nhập tên đề và mã đề");
      return;
    }
    run(
      () => (isNew ? createExam(token, infoPayload(info)) : updateExam(token, id, infoPayload(info))),
      (data) => (isNew ? navigate(`/giang-vien/bo-de/${data.id}`, { replace: true }) : reload()),
    );
  }

  function saveItems() {
    run(() => saveExamItems(token, id, itemsPayload(items)), () => reload());
  }

  function action(name) {
    run(() => examAction(token, id, name), async (data) => {
      if (name === "ban-nhap" && String(data.id) !== String(id)) navigate(`/giang-vien/bo-de/${data.id}`);
      else await reload();
    });
  }

  function remove() {
    if (!window.confirm("Xóa đề nháp này?")) return;
    run(() => deleteExam(token, id), () => navigate("/giang-vien/bo-de"));
  }

  // Thêm câu từ ngân hàng: ngữ liệu thì thêm toàn bộ câu con
  async function addQuestion(row) {
    setError("");
    try {
      if (row.dang === "ngu_lieu") {
        const detail = await getQuestion(token, row.id);
        const present = new Set(items.map((i) => i.cau_hoi_id));
        const added = detail.cau_con.filter((c) => !present.has(c.id)).map((c) => ({
          cau_hoi_id: c.id, phan: DEFAULT_PART[row.ky_nang], la_cau_vi_du: false, ky_nang: row.ky_nang,
          cau_cha_id: detail.id, cau_hoi: c,
        }));
        setExam((e) => ({ ...e, ngu_lieu: { ...e.ngu_lieu, [detail.id]: detail } }));
        setItems((list) => [...list, ...added]);
      } else {
        const detail = await getQuestion(token, row.id);
        setItems((list) => (list.some((i) => i.cau_hoi_id === row.id) ? list : [
          ...list,
          { cau_hoi_id: row.id, phan: DEFAULT_PART[row.ky_nang], la_cau_vi_du: false, ky_nang: row.ky_nang, cau_cha_id: null, cau_hoi: detail },
        ]));
      }
    } catch (err) {
      setError(err?.message || "Không thêm được câu");
    }
  }

  function updateItem(index, patch) {
    setItems((list) => list.map((item, i) => (i === index ? { ...item, ...patch } : item)));
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
  if (!isNew && !exam) return <p role="alert">{error || "Không tìm thấy đề"}</p>;

  let counter = 0;
  return (
    <section className="lv-page">
      <Link to="/giang-vien/bo-de" className="lv-back"><Icon name="back" size={18} /> Đề thi thử HSK</Link>
      <div className="lv-page__head">
        <div className="lv-page__intro">
          <h1>{isNew ? "Tạo đề thi thử" : exam.ten}</h1>
          <p>{isNew ? "Nhập thông tin đề, sau đó thêm câu từ ngân hàng câu đã đăng." : `Mã đề ${exam.ma_de} · ${items.filter((i) => !i.la_cau_vi_du).length} câu tính điểm`}</p>
        </div>
        {exam && <span className="lv-head-meta"><StatusBadge status={status} /> Bản {exam.phien_ban}</span>}
      </div>

      {exam && !editable && isLatest && (
        <p className="lv-hint">
          Đề đã {status === "da_dang" ? "đăng" : "ẩn"}, không sửa trực tiếp. Bấm <strong>Tạo bản nháp để sửa</strong>;
          bản hiện tại vẫn dùng cho học viên đến khi bạn đăng bản mới.
        </p>
      )}
      {exam && !isLatest && <p className="lv-hint">Đây là phiên bản cũ, chỉ để xem.</p>}

      <fieldset className="lv-card" disabled={busy || !editable}>
        <legend>Thông tin đề</legend>
        <div className="lv-grid-3">
          <div className="lv-field">
            <label htmlFor="e-level">Cấp độ</label>
            <select id="e-level" value={info.cap_do_id} onChange={(e) => setInfo({ ...info, cap_do_id: e.target.value })}>
              {levels.map((l) => <option key={l.ma_cap_do} value={l.ma_cap_do}>{l.ten_cap_do}</option>)}
            </select>
          </div>
          <div className="lv-field">
            <label htmlFor="e-code">Mã đề</label>
            <input id="e-code" value={info.ma_de} maxLength={30} placeholder="VD: HSK1-01"
              disabled={exam && exam.phien_ban > 1} onChange={(e) => setInfo({ ...info, ma_de: e.target.value })} />
          </div>
          <div className="lv-field">
            <label htmlFor="e-time">Thời lượng (phút)</label>
            <input id="e-time" type="number" min="1" max="300" value={info.thoi_luong_phut}
              onChange={(e) => setInfo({ ...info, thoi_luong_phut: e.target.value })} />
          </div>
        </div>
        <div className="lv-field">
          <label htmlFor="e-name">Tên đề</label>
          <input id="e-name" value={info.ten} maxLength={150} onChange={(e) => setInfo({ ...info, ten: e.target.value })} />
        </div>
        <div className="lv-field">
          <label htmlFor="e-source">Nguồn (nếu có)</label>
          <input id="e-source" value={info.nguon} maxLength={255} onChange={(e) => setInfo({ ...info, nguon: e.target.value })} />
        </div>
        <MediaInput kind="audio" label="Âm thanh chung của phần Nghe (nếu cả đề dùng 1 tệp)" value={info.tep_audio_chung}
          onChange={(v) => setInfo({ ...info, tep_audio_chung: v })} disabled={busy || !editable} />
        {editable && (
          <div className="lv-actions">
            <button type="button" className="xbtn" onClick={saveInfo} disabled={busy || !infoDirty}>
              {isNew ? "Tạo đề" : "Lưu thông tin"}
            </button>
          </div>
        )}
      </fieldset>

      {exam && (
        <div className="lv-editor">
          <div className="lv-editor__form">
            <fieldset className="lv-card" disabled={busy || !editable}>
              <legend>Câu trong đề ({items.filter((i) => !i.la_cau_vi_du).length} câu tính điểm)</legend>
              {items.length === 0 && <p className="lv-muted">Chưa có câu nào. Thêm từ ngân hàng câu đã đăng bên dưới.</p>}
              <ol className="lv-items">
                {items.map((item, index) => (
                  <li key={item.cau_hoi_id} className="lv-item">
                    <span className="lv-item__no">{index + 1}</span>
                    <span className="lv-item__text">
                      <span className="lv-cell-sub">
                        #{item.cau_hoi.ma_goc_id} · {SKILL_LABELS[item.ky_nang]} · {DANG_LABELS[item.cau_hoi.dang]}
                        {item.cau_cha_id && ` · thuộc ngữ liệu #${parents[item.cau_cha_id]?.ma_goc_id ?? item.cau_cha_id}`}
                        {item.cau_hoi.trang_thai !== "da_dang" && " · chưa đăng"}
                      </span>
                      <span className="zh">{item.cau_hoi.noi_dung || "(âm thanh / hình)"}</span>
                    </span>
                    <span className="lv-item__ctrl">
                      <select aria-label={`Phần của câu ${index + 1}`} value={item.phan ?? ""} onChange={(e) => updateItem(index, { phan: e.target.value })}>
                        {[1, 2, 3, 4].map((p) => <option key={p} value={p}>Phần {p}</option>)}
                      </select>
                      <label className="lv-inline">
                        <input type="checkbox" checked={item.la_cau_vi_du} onChange={(e) => updateItem(index, { la_cau_vi_du: e.target.checked })} /> Ví dụ
                      </label>
                      <button type="button" className="xlink" aria-label={`Đưa câu ${index + 1} lên`} onClick={() => moveItem(index, -1)} disabled={index === 0}><Icon name="up" size={18} /></button>
                      <button type="button" className="xlink" aria-label={`Đưa câu ${index + 1} xuống`} onClick={() => moveItem(index, 1)} disabled={index === items.length - 1}><Icon name="down" size={18} /></button>
                      <button type="button" className="xlink xlink--danger" onClick={() => setItems((l) => l.filter((_, i) => i !== index))}>Gỡ</button>
                    </span>
                  </li>
                ))}
              </ol>
              {editable && (
                <div className="lv-actions">
                  <button type="button" className="xbtn" onClick={saveItems} disabled={busy || !itemsDirty}>Lưu danh sách câu</button>
                  {itemsDirty && <span className="lv-dirty">Có thay đổi chưa lưu</span>}
                </div>
              )}
            </fieldset>

            {editable && <QuestionPicker token={token} capDoId={exam.cap_do_id} purpose="thi_thu" chosen={items} onAdd={addQuestion} title="Ngân hàng câu đã đăng (dùng cho Thi thử, cùng cấp)" />}

            {error && <p role="alert" className="lv-alert">{error}</p>}
            {notice && <p role="status" className="lv-notice">{notice}</p>}

            {isLatest && (
              <div className="lv-actions">
                {status === "nhap" && (
                  <button type="button" className="xbtn" onClick={() => action("dang")}
                    disabled={busy || itemsDirty || infoDirty} title={itemsDirty || infoDirty ? "Lưu thay đổi trước" : undefined}>
                    Đăng đề
                  </button>
                )}
                {status !== "nhap" && <button type="button" className="xbtn" onClick={() => action("ban-nhap")} disabled={busy}>Tạo bản nháp để sửa</button>}
                {status === "da_dang" && <button type="button" className="xbtn xbtn--ghost" onClick={() => action("an")} disabled={busy}>Ẩn đề</button>}
                {status === "da_an" && <button type="button" className="xbtn xbtn--ghost" onClick={() => action("hien")} disabled={busy}>Hiện lại</button>}
                {status === "nhap" && <button type="button" className="xbtn xbtn--danger" onClick={remove} disabled={busy}>Xóa nháp</button>}
              </div>
            )}
          </div>

          <aside className="lv-editor__preview" aria-label="Xem trước đề">
            <h2>Xem trước</h2>
            {info.tep_audio_chung && <p className="lv-muted">Có âm thanh chung cho phần Nghe.</p>}
            {items.map((item, index) => {
              const prev = items[index - 1];
              const showPassage = item.cau_cha_id && (!prev || prev.cau_cha_id !== item.cau_cha_id) && parents[item.cau_cha_id];
              const number = item.la_cau_vi_du ? null : ++counter;
              return (
                <div key={item.cau_hoi_id}>
                  {(!prev || String(prev.phan) !== String(item.phan)) && <h3 className="lv-part">Phần {item.phan}</h3>}
                  {showPassage && <SharedPassage q={parents[item.cau_cha_id]} />}
                  {item.la_cau_vi_du && <p className="lv-muted">Ví dụ</p>}
                  <QuestionPreview q={item.cau_hoi} number={number} />
                </div>
              );
            })}
          </aside>
        </div>
      )}
    </section>
  );
}
