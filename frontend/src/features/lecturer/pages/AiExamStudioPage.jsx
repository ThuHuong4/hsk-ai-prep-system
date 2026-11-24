import { useEffect, useState } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";

import { useAuth } from "../../auth/context/AuthContext.jsx";
import { aiComposeExam, aiCreateExam } from "../api/lecturerApi.js";
import Icon from "../../../shared/components/Icon.jsx";
import { useLevels } from "../hooks/useLevels.js";
import { DANG_LABELS, SKILL_LABELS } from "../utils/labels.js";
import "../styles/lecturer.css";

/**
 * Ghép đề thi thử với AI:
 * Giảng viên đặt cấu trúc phần -> AI CHỌN câu đã duyệt trong ngân hàng (không tự viết câu mới vào đề)
 * -> Giảng viên trao đổi với AI để đổi câu, gỡ câu không ưng, soạn bù phần thiếu với AI
 * -> "Tạo đề nháp" -> mở trang soạn đề kiểm tra rồi bấm Đăng (= duyệt).
 */
const PARTS = ["nghe", "doc", "viet"];
// Gợi ý mặc định theo cấu trúc đề HSK 1–4 (Nghe, Đọc, Viết; thời lượng phút) — Giảng viên sửa được
const DEFAULTS = {
  "HSK 1": { nghe: 20, doc: 20, viet: 0, phut: 40 },
  "HSK 2": { nghe: 35, doc: 25, viet: 0, phut: 55 },
  "HSK 3": { nghe: 40, doc: 30, viet: 10, phut: 90 },
  "HSK 4": { nghe: 45, doc: 40, viet: 15, phut: 105 },
};

function defaultsFor(levelName) {
  return DEFAULTS[(levelName || "").trim().toUpperCase().replace("HSK", "HSK ").replace(/\s+/g, " ")] || { nghe: 10, doc: 10, viet: 0, phut: 45 };
}

export default function AiExamStudioPage() {
  const { token } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const levels = useLevels();
  const [info, setInfo] = useState({ cap_do_id: "", ten: "", ma_de: "", thoi_luong_phut: 40 });
  const [parts, setParts] = useState({ nghe: 20, doc: 20, viet: 0 });
  const [request, setRequest] = useState("");
  const [items, setItems] = useState([]);
  const [missing, setMissing] = useState([]);
  const [chat, setChat] = useState([]);
  const [message, setMessage] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    // Trợ lý AI có thể mở trang này kèm cấp đã chọn
    if (!info.cap_do_id && levels.length) changeLevel(location.state?.cap_do_id ?? levels[0].ma_cap_do);
  }, [levels]); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    if (location.state?.cap_do_id && levels.length) changeLevel(location.state.cap_do_id);
  }, [location.key]); // eslint-disable-line react-hooks/exhaustive-deps

  function changeLevel(id) {
    const name = levels.find((l) => l.ma_cap_do === Number(id))?.ten_cap_do;
    const d = defaultsFor(name);
    setInfo((x) => ({ ...x, cap_do_id: Number(id), thoi_luong_phut: d.phut }));
    setParts({ nghe: d.nghe, doc: d.doc, viet: d.viet });
    setItems([]);
    setMissing([]);
    setChat([]);
  }

  async function compose(text) {
    setBusy(true);
    setError("");
    const history = text ? [...chat, { vai_tro: "gv", noi_dung: text }] : chat;
    setChat(history);
    try {
      const data = await aiComposeExam(token, {
        cap_do_id: Number(info.cap_do_id),
        cau_truc: PARTS.map((k) => ({ ky_nang: k, so_cau: Number(parts[k]) || 0 })),
        yeu_cau: request.trim() || null,
        tin_nhan: text || null,
        lich_su: chat.slice(-10),
        hien_tai: items.map((i) => i.cau_hoi_id),
      });
      setItems(data.cau_hoi || []);
      setMissing(data.thieu || []);
      setChat([...history, { vai_tro: "ai", noi_dung: data.tra_loi }]);
    } catch (err) {
      setChat(chat);
      setError(err?.message || "AI chưa ghép được đề, vui lòng thử lại");
    } finally {
      setBusy(false);
    }
  }

  function send(e) {
    e.preventDefault();
    const text = message.trim();
    if (!text) return;
    setMessage("");
    compose(text);
  }

  // Gỡ một câu; câu thuộc ngữ liệu chung thì gỡ cả cụm
  function remove(item) {
    setItems((list) => list.filter((i) => (item.cau_cha_id ? i.cau_cha_id !== item.cau_cha_id : i.cau_hoi_id !== item.cau_hoi_id)));
  }

  async function createDraft() {
    setBusy(true);
    setError("");
    try {
      const data = await aiCreateExam(token, {
        thong_tin: {
          cap_do_id: Number(info.cap_do_id),
          ten: info.ten.trim(),
          ma_de: info.ma_de.trim(),
          nguon: null,
          thoi_luong_phut: Number(info.thoi_luong_phut) || null,
          tep_audio_chung: null,
        },
        cau_hoi: items.map((i) => ({ cau_hoi_id: i.cau_hoi_id, phan: i.phan, la_cau_vi_du: false })),
      });
      navigate(`/giang-vien/bo-de/${data.id}`);
    } catch (err) {
      setError(err?.message || "Không tạo được đề");
      setBusy(false);
    }
  }

  const canCreate = items.length > 0 && info.ten.trim() && info.ma_de.trim().length >= 2 && !busy;

  return (
    <section className="lv-page">
      <Link to="/giang-vien/bo-de/ai" className="lv-back"><Icon name="back" size={18} /> Tạo đề với AI</Link>
      <div className="lv-page__head">
        <div className="lv-page__intro">
          <h1>Ghép đề từ câu đã duyệt</h1>
          <p>
            AI chỉ chọn câu đã duyệt trong ngân hàng (đang đăng, bật “Dùng cho Thi thử”), không tự viết câu mới vào đề.
            Bạn trao đổi với AI để đổi câu, rồi tạo đề nháp và tự bấm <b>Đăng</b> sau khi kiểm tra.
          </p>
        </div>
      </div>

      <form className="lv-card lv-ai__form" onSubmit={(e) => { e.preventDefault(); compose(""); }}>
        <fieldset disabled={busy || !levels.length}>
          <div className="lv-grid-3">
            <div className="lv-field">
              <label htmlFor="ex-level">Cấp độ</label>
              <select id="ex-level" value={info.cap_do_id} onChange={(e) => changeLevel(e.target.value)}>
                {levels.map((l) => <option key={l.ma_cap_do} value={l.ma_cap_do}>{l.ten_cap_do}</option>)}
              </select>
            </div>
            {PARTS.map((k, i) => (
              <div key={k} className="lv-field">
                <label htmlFor={`ex-${k}`}>Phần {i + 1} – {SKILL_LABELS[k]} (số câu)</label>
                <input id={`ex-${k}`} type="number" min={0} max={100} value={parts[k]}
                  onChange={(e) => setParts((p) => ({ ...p, [k]: e.target.value }))} />
              </div>
            ))}
          </div>
          <p className="lv-help">Số câu và thời lượng điền sẵn theo cấu trúc đề HSK của cấp đã chọn; bạn sửa được.</p>
          <div className="lv-field">
            <label htmlFor="ex-req">Yêu cầu thêm cho AI (không bắt buộc)</label>
            <textarea id="ex-req" rows={2} maxLength={1000} placeholder="Ví dụ: ưu tiên chủ đề mua sắm, tránh câu đã dùng nhiều"
              value={request} onChange={(e) => setRequest(e.target.value)} />
          </div>
          <button type="submit" className="xbtn">{busy ? "AI đang chọn câu…" : items.length ? "AI ghép lại từ đầu" : "AI ghép đề"}</button>
        </fieldset>
      </form>

      {error && <p role="alert" className="lv-alert">{error}</p>}

      {(chat.length > 0 || items.length > 0) && (
        <section className="lv-card lv-ai__advice" aria-label="Trao đổi với AI về đề">
          <h2 className="lv-ai__title">Trao đổi với AI</h2>
          <div className="lv-ai__chat">
            {chat.map((m, i) => (
              <p key={i} className={m.vai_tro === "ai" ? "lv-ai__msg lv-ai__msg--ai" : "lv-ai__msg"}>
                <b>{m.vai_tro === "ai" ? "AI" : "Bạn"}:</b> {m.noi_dung}
              </p>
            ))}
          </div>
          <form className="lv-ai__ask" onSubmit={send}>
            <input value={message} maxLength={1000} disabled={busy} aria-label="Nhắn cho AI về đề"
              placeholder="Ví dụ: phần Đọc nhiều câu phủ định quá, đổi bớt sang câu thời gian"
              onChange={(e) => setMessage(e.target.value)} />
            <button type="submit" className="xbtn xbtn--sm" disabled={busy || !message.trim()}>{busy ? "Đang xử lý…" : "Gửi"}</button>
          </form>
        </section>
      )}

      {missing.length > 0 && (
        <div className="lv-ai__warn">
          <b>Ngân hàng chưa đủ câu đã duyệt:</b>
          <ul>
            {missing.map((m) => (
              <li key={m.ky_nang}>
                {SKILL_LABELS[m.ky_nang]}: thiếu {m.so_thieu} câu (đang có {m.co_san}).{" "}
                <button type="button" className="xlink" onClick={() => navigate("/giang-vien/cau-hoi/ai", {
                  state: { plan: { cap_do_id: Number(info.cap_do_id), ky_nang: m.ky_nang, so_luong: Math.min(20, m.so_thieu) } },
                })}>
                  Soạn bù với AI
                </button>
              </li>
            ))}
          </ul>
        </div>
      )}

      {items.length > 0 && (
        <section className="lv-card" aria-label="Câu AI đã chọn">
          {PARTS.filter((k) => items.some((i) => i.ky_nang === k)).map((k) => (
            <div key={k} className="lv-ai__part">
              <h3>Phần {PARTS.indexOf(k) + 1} – {SKILL_LABELS[k]} ({items.filter((i) => i.ky_nang === k).length} câu)</h3>
              <ol>
                {items.filter((i) => i.ky_nang === k).map((i) => (
                  <li key={i.cau_hoi_id}>
                    <span className="lv-ai__qid">#{i.cau_hoi_id}</span>
                    <span>
                      {DANG_LABELS[i.dang]}{i.nhom ? ` · ${i.nhom}` : ""}{i.cau_cha_id ? ` · ngữ liệu #${i.cau_cha_id}` : ""}
                      <br />
                      <span className="zh">{i.noi_dung}</span>
                    </span>
                    <button type="button" className="xbtn xbtn--ghost xbtn--sm" onClick={() => remove(i)} disabled={busy}
                      aria-label={`Gỡ câu ${i.cau_hoi_id}`}>Gỡ</button>
                  </li>
                ))}
              </ol>
            </div>
          ))}

          <div className="lv-grid-3">
            <div className="lv-field">
              <label htmlFor="ex-name">Tên đề</label>
              <input id="ex-name" maxLength={150} value={info.ten} onChange={(e) => setInfo((x) => ({ ...x, ten: e.target.value }))}
                placeholder="Ví dụ: Đề thi thử HSK 1 – Số 3" />
            </div>
            <div className="lv-field">
              <label htmlFor="ex-code">Mã đề</label>
              <input id="ex-code" maxLength={30} value={info.ma_de} onChange={(e) => setInfo((x) => ({ ...x, ma_de: e.target.value }))}
                placeholder="Ví dụ: H1_AI_03" />
            </div>
            <div className="lv-field">
              <label htmlFor="ex-time">Thời lượng (phút)</label>
              <input id="ex-time" type="number" min={1} max={300} value={info.thoi_luong_phut}
                onChange={(e) => setInfo((x) => ({ ...x, thoi_luong_phut: e.target.value }))} />
            </div>
          </div>
          <div className="lv-actions">
            <button type="button" className="xbtn" onClick={createDraft} disabled={!canCreate}>Tạo đề nháp ({items.length} câu)</button>
            <span className="lv-help">Đề tạo ra ở trạng thái nháp, nguồn ghi “Ghép với AI từ ngân hàng câu hỏi đã duyệt”.</span>
          </div>
        </section>
      )}
    </section>
  );
}
