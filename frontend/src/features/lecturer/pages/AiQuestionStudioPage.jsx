import { useEffect, useState } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";

import { useAuth } from "../../auth/context/AuthContext.jsx";
import {
  aiApproveDrafts, aiChatDraft, aiDraftQuestions, aiMakeAudio, aiMakeImage, aiReviewDrafts, aiSuggestPlan,
} from "../api/lecturerApi.js";
import Icon from "../../../shared/components/Icon.jsx";
import MediaInput from "../components/MediaInput.jsx";
import QuestionPreview from "../components/QuestionPreview.jsx";
import { useKnowledgeGroups } from "../hooks/useKnowledgeGroups.js";
import { useLevels } from "../hooks/useLevels.js";
import { DANG_LABELS, SKILL_LABELS } from "../utils/labels.js";
import "../styles/lecturer.css";

/**
 * Soạn câu với AI (Mục 11 nghiệp vụ bổ sung):
 * AI soạn lô câu + tự gắn nhóm kiến thức + tự soát lỗi -> Giảng viên trao đổi với AI từng câu
 * (AI chỉ ĐỀ XUẤT bản sửa, Giảng viên bấm "Dùng bản này" mới thay) -> Giảng viên bấm Duyệt mới lưu và đăng.
 * Danh sách nháp giữ tạm trong phiên trình duyệt (sessionStorage) để không mất khi chuyển trang.
 */
const AI_TYPES = ["chon_mot", "dung_sai", "sap_xep", "dien_chu", "viet_mo", "dich_cau"];
const STORE_KEY = "xianglingo-ai-soan-cau";
let seed = 0;
const newKey = () => `ai${Date.now()}_${seed++}`;

function loadStore() {
  try {
    const data = JSON.parse(sessionStorage.getItem(STORE_KEY) || "[]");
    return Array.isArray(data) ? data.map((c) => ({ ...c, busy: false })) : [];
  } catch {
    return [];
  }
}

function saveStore(cards) {
  try {
    sessionStorage.setItem(STORE_KEY, JSON.stringify(cards.filter((c) => c.trang_thai !== "da_duyet")));
  } catch {
    // trình duyệt chặn lưu trữ: chỉ giữ trong trang
  }
}

const needsAudio = (q) => q.ky_nang === "nghe" && !q.tep_audio;
const isClean = (c) =>
  c.trang_thai === "cho" && !c.loi && Array.isArray(c.van_de_ai) && c.van_de_ai.length === 0 && !needsAudio(c.cau_hoi) &&
  !(c.trung_lap?.length > 0);

function toCard(data) {
  return { key: newKey(), ...data, chat: [], de_xuat: null, trang_thai: "cho", thong_bao: "", busy: false };
}

export default function AiQuestionStudioPage() {
  const { token } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const levels = useLevels();
  const groups = useKnowledgeGroups();
  // "Soạn bù với AI" từ trang Ghép đề: điền sẵn cấp, kỹ năng, số câu còn thiếu
  const plan = location.state?.plan;
  const [req, setReq] = useState({
    cap_do_id: plan?.cap_do_id ?? "", ky_nang: plan?.ky_nang ?? "doc", dang: plan?.dang ?? "chon_mot", chu_de: plan?.chu_de ?? "",
    yeu_cau: "", so_luong: plan?.so_luong ?? 5, dung_thi_thu: plan?.loai !== "soan_cau" && Boolean(plan),
  });
  const [cards, setCards] = useState(loadStore);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [advice, setAdvice] = useState({ chat: [], plans: [], busy: false, error: "" });
  const [question, setQuestion] = useState("");

  useEffect(() => {
    if (!req.cap_do_id && levels.length) setReq((r) => ({ ...r, cap_do_id: levels[0].ma_cap_do }));
  }, [levels, req.cap_do_id]);
  useEffect(() => saveStore(cards), [cards]);
  // Mở lại trang này từ Trợ lý AI / Ghép đề khi đang ở sẵn trang: áp gợi ý mới vào form
  useEffect(() => {
    if (!plan) return;
    setReq((r) => ({
      ...r, cap_do_id: plan.cap_do_id ?? r.cap_do_id, ky_nang: plan.ky_nang ?? r.ky_nang, dang: plan.dang ?? r.dang,
      chu_de: plan.chu_de ?? r.chu_de, so_luong: plan.so_luong ?? r.so_luong, dung_thi_thu: plan.loai !== "soan_cau",
    }));
  }, [location.key]); // eslint-disable-line react-hooks/exhaustive-deps

  const setField = (patch) => setReq((r) => ({ ...r, ...patch }));
  const patchCard = (key, patch) => setCards((list) => list.map((c) => (c.key === key ? { ...c, ...patch } : c)));
  const pending = cards.filter((c) => c.trang_thai !== "da_duyet");
  const clean = pending.filter(isClean);
  const missingAudioCards = pending.filter((c) => needsAudio(c.cau_hoi));
  const [audioBatchBusy, setAudioBatchBusy] = useState(false);

  async function makeAudioForCard(card) {
    const q = card.cau_hoi;
    const script = (q.loi_nghe || q.noi_dung || "").trim();
    if (!script) throw new Error("Câu này chưa có lời nghe để đọc");
    const data = await aiMakeAudio(token, Number(q.cap_do_id) || 1, script);
    setCards((list) => list.map((c) => {
      if (c.key !== card.key) return c;
      const nextQ = { ...c.cau_hoi, tep_audio: data.duong_dan };
      return { ...c, cau_hoi: nextQ, luu_y: [] };
    }));
    return data.duong_dan;
  }

  async function fillMissingAudio(targetCards) {
    if (!targetCards.length || audioBatchBusy) return;
    setAudioBatchBusy(true);
    try {
      for (const c of targetCards) {
        try {
          await makeAudioForCard(c); // eslint-disable-line no-await-in-loop
        } catch {
          // câu lỗi mạng giữ nguyên để Giảng viên bấm tạo lại riêng
        }
      }
    } finally {
      setAudioBatchBusy(false);
    }
  }

  // Hỏi AI nên soạn gì: AI dựa vào số câu thật trong ngân hàng (theo cấp/kỹ năng đang chọn)
  async function askAdvice(e) {
    e?.preventDefault();
    const text = question.trim();
    const chat = text ? [...advice.chat, { vai_tro: "gv", noi_dung: text }] : advice.chat;
    setAdvice((a) => ({ ...a, chat, busy: true, error: "" }));
    setQuestion("");
    try {
      const data = await aiSuggestPlan(token, {
        cap_do_id: req.cap_do_id ? Number(req.cap_do_id) : null,
        ky_nang: req.ky_nang || null,
        tin_nhan: text || null,
        lich_su: advice.chat.slice(-10),
      });
      setAdvice({ chat: [...chat, { vai_tro: "ai", noi_dung: data.tra_loi }], plans: data.goi_y || [], busy: false, error: "" });
    } catch (err) {
      setAdvice((a) => ({ ...a, chat: advice.chat, busy: false, error: err?.message || "AI chưa trả lời được" }));
    }
  }

  function applyPlan(plan) {
    const next = { ...req, ...plan, chu_de: plan.chu_de || "", yeu_cau: plan.yeu_cau || "" };
    delete next.ly_do;
    setReq(next);
    return next;
  }

  function generate(e) {
    e.preventDefault();
    runGenerate(req);
  }

  async function runGenerate(params) {
    setBusy(true);
    setError("");
    setNotice("");
    try {
      const data = await aiDraftQuestions(token, {
        cap_do_id: Number(params.cap_do_id),
        ky_nang: params.ky_nang,
        dang: params.dang,
        chu_de: params.chu_de.trim() || null,
        so_luong: Math.min(20, Math.max(1, Number(params.so_luong) || 1)),
        yeu_cau: params.yeu_cau.trim() || null,
        dung_thi_thu: Boolean(params.dung_thi_thu),
      });
      const freshCards = (data.ban_nhap || []).map(toCard);
      setCards((list) => [...freshCards, ...list]);
      setNotice(data.ghi_chu || `AI đã soạn ${freshCards.length} câu. Xem, nghe/xem hình, trao đổi với AI nếu cần, rồi duyệt.`);
      const listenCards = freshCards.filter((c) => needsAudio(c.cau_hoi) && (c.cau_hoi.loi_nghe || c.cau_hoi.noi_dung));
      if (listenCards.length) fillMissingAudio(listenCards);
    } catch (err) {
      setError(err?.message || "AI chưa soạn được, vui lòng thử lại");
    } finally {
      setBusy(false);
    }
  }

  async function approve(list) {
    if (!list.length) return;
    list.forEach((c) => patchCard(c.key, { busy: true, thong_bao: "" }));
    try {
      const data = await aiApproveDrafts(token, list.map((c) => c.cau_hoi));
      (data.ket_qua || []).forEach((r) => {
        const card = list[r.stt - 1];
        if (!card) return;
        if (!r.loi) patchCard(card.key, { busy: false, trang_thai: "da_duyet", id: r.id, thong_bao: "" });
        else patchCard(card.key, { busy: false, id: r.id, thong_bao: r.loi, trang_thai: r.id ? "da_luu_nhap" : "cho" });
      });
    } catch (err) {
      list.forEach((c) => patchCard(c.key, { busy: false, thong_bao: err?.message || "Duyệt thất bại" }));
    }
  }

  function approveOne(card) {
    const warn = !Array.isArray(card.van_de_ai) || card.van_de_ai.length > 0;
    if (warn && !window.confirm("Câu này còn cảnh báo (hoặc AI chưa soát được). Bạn đã tự kiểm tra và vẫn duyệt?")) return;
    approve([card]);
  }

  function approveClean() {
    if (!window.confirm(`Duyệt và đăng ${clean.length} câu không có cảnh báo? Câu sẽ dùng ngay cho học viên.`)) return;
    approve(clean);
  }

  async function recheck(card) {
    patchCard(card.key, { busy: true, thong_bao: "" });
    try {
      const data = await aiReviewDrafts(token, [card.cau_hoi]);
      const r = data.ban_nhap?.[0];
      patchCard(card.key, { busy: false, loi: r?.loi ?? null, van_de_ai: r?.van_de_ai ?? null, luu_y: r?.luu_y || [], trung_lap: r?.trung_lap || [] });
    } catch (err) {
      patchCard(card.key, { busy: false, thong_bao: err?.message || "AI chưa soát được" });
    }
  }

  async function ask(card, message) {
    const chat = [...card.chat, { vai_tro: "gv", noi_dung: message }];
    patchCard(card.key, { busy: true, chat, thong_bao: "" });
    try {
      const data = await aiChatDraft(token, { cau_hoi: card.cau_hoi, tin_nhan: message, lich_su: card.chat.slice(-10) });
      patchCard(card.key, { busy: false, chat: [...chat, { vai_tro: "ai", noi_dung: data.tra_loi }], de_xuat: data.de_xuat || null });
    } catch (err) {
      patchCard(card.key, { busy: false, chat: card.chat, thong_bao: err?.message || "AI chưa trả lời được" });
    }
  }

  function acceptProposal(card) {
    const p = card.de_xuat;
    patchCard(card.key, { cau_hoi: p.cau_hoi, loi: p.loi, van_de_ai: p.van_de_ai, luu_y: p.luu_y, trung_lap: p.trung_lap || [], de_xuat: null,
      chat: [...card.chat, { vai_tro: "gv", noi_dung: "(Đã dùng bản AI đề xuất)" }] });
  }

  function changeQuestion(card, patch) {
    const q = { ...card.cau_hoi, ...patch };
    // Chỉ đổi nhóm kiến thức hoặc tệp âm thanh: nội dung câu giữ nguyên nên giữ kết quả AI soát
    patchCard(card.key, { cau_hoi: q, luu_y: needsAudio(q) ? card.luu_y : [] });
  }

  function editByHand(card) {
    setCards((list) => list.filter((c) => c.key !== card.key));
    navigate("/giang-vien/cau-hoi/moi", { state: { draft: card.cau_hoi } });
  }

  return (
    <section className="lv-page">
      <Link to="/giang-vien/cau-hoi" className="lv-back"><Icon name="back" size={18} /> Ngân hàng câu hỏi</Link>
      <div className="lv-page__head">
        <div className="lv-page__intro">
          <h1>Soạn câu với AI</h1>
          <p>
            AI soạn, gắn nhóm kiến thức và tự soát lỗi. Bạn trao đổi với AI để chỉnh từng câu; câu chỉ được lưu và đăng
            khi bạn bấm <b>Duyệt</b>. Hệ thống ghi nguồn “Soạn với AI”, người duyệt và thời điểm duyệt.
          </p>
        </div>
      </div>

      <section className="lv-card lv-ai__advice" aria-labelledby="ai-advice-title">
        <h2 id="ai-advice-title" className="lv-ai__title">Hỏi AI nên soạn gì</h2>
        <p className="lv-help">
          AI xem số câu đang có trong ngân hàng (theo cấp và kỹ năng đang chọn bên dưới) rồi gợi ý chỗ còn thiếu.
          Bạn hỏi lại hoặc trao đổi thêm được.
        </p>
        {advice.chat.length > 0 && (
          <div className="lv-ai__chat">
            {advice.chat.map((m, i) => (
              <p key={i} className={m.vai_tro === "ai" ? "lv-ai__msg lv-ai__msg--ai" : "lv-ai__msg"}>
                <b>{m.vai_tro === "ai" ? "AI" : "Bạn"}:</b> {m.noi_dung}
              </p>
            ))}
          </div>
        )}
        {advice.plans.length > 0 && (
          <ul className="lv-ai__plans">
            {advice.plans.map((p, i) => (
              <li key={i} className="lv-ai__plan">
                <b>
                  {levels.find((l) => l.ma_cap_do === p.cap_do_id)?.ten_cap_do || `Cấp ${p.cap_do_id}`} ·{" "}
                  {SKILL_LABELS[p.ky_nang]} · {DANG_LABELS[p.dang]} · {p.so_luong} câu
                </b>
                {p.chu_de && <span>Chủ đề: {p.chu_de}</span>}
                {p.ly_do && <small>{p.ly_do}</small>}
                <div className="lv-actions">
                  <button type="button" className="xbtn xbtn--ghost xbtn--sm" onClick={() => applyPlan(p)} disabled={busy}>
                    Điền vào form
                  </button>
                  <button type="button" className="xbtn xbtn--sm" onClick={() => runGenerate(applyPlan(p))} disabled={busy}>
                    Soạn luôn
                  </button>
                </div>
              </li>
            ))}
          </ul>
        )}
        {advice.error && <p role="alert" className="lv-alert">{advice.error}</p>}
        <form className="lv-ai__ask" onSubmit={askAdvice}>
          <input value={question} maxLength={1000} disabled={advice.busy} aria-label="Hỏi AI nên soạn gì"
            placeholder="Ví dụ: HSK 2 còn thiếu dạng nào? Gợi ý chủ đề luyện nghe giờ giấc"
            onChange={(e) => setQuestion(e.target.value)} />
          <button type="submit" className="xbtn xbtn--sm" disabled={advice.busy}>
            {advice.busy ? "AI đang xem…" : question.trim() ? "Gửi" : "AI gợi ý ngay"}
          </button>
        </form>
      </section>

      <form className="lv-card lv-ai__form" onSubmit={generate}>
        <fieldset disabled={busy || !levels.length}>
          <div className="lv-grid-3">
            <div className="lv-field">
              <label htmlFor="ai-level">Cấp độ</label>
              <select id="ai-level" value={req.cap_do_id} onChange={(e) => setField({ cap_do_id: e.target.value })}>
                {levels.map((l) => <option key={l.ma_cap_do} value={l.ma_cap_do}>{l.ten_cap_do}</option>)}
              </select>
            </div>
            <div className="lv-field">
              <label htmlFor="ai-skill">Kỹ năng</label>
              <select id="ai-skill" value={req.ky_nang} onChange={(e) => setField({ ky_nang: e.target.value })}>
                {Object.entries(SKILL_LABELS).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
              </select>
            </div>
            <div className="lv-field">
              <label htmlFor="ai-type">Dạng câu</label>
              <select id="ai-type" value={req.dang} onChange={(e) => setField({ dang: e.target.value })}>
                {AI_TYPES.map((t) => <option key={t} value={t}>{DANG_LABELS[t]}</option>)}
              </select>
            </div>
          </div>
          <div className="lv-ai__row">
            <div className="lv-field">
              <label htmlFor="ai-topic">Chủ đề (để trống: AI tự chọn)</label>
              <input id="ai-topic" maxLength={200} placeholder="Ví dụ: hẹn giờ gặp bạn, phủ định 不/没"
                value={req.chu_de} onChange={(e) => setField({ chu_de: e.target.value })} />
            </div>
            <div className="lv-field lv-ai__count">
              <label htmlFor="ai-count">Số câu</label>
              <input id="ai-count" type="number" min={1} max={20} value={req.so_luong}
                onChange={(e) => setField({ so_luong: e.target.value })} />
            </div>
          </div>
          <div className="lv-field">
            <label htmlFor="ai-extra">Yêu cầu thêm (không bắt buộc)</label>
            <textarea id="ai-extra" rows={2} maxLength={1000} placeholder="Ví dụ: dùng từ 已经, câu ngắn dưới 12 chữ"
              value={req.yeu_cau} onChange={(e) => setField({ yeu_cau: e.target.value })} />
          </div>
          <label className="lv-inline">
            <input type="checkbox" checked={req.dung_thi_thu} onChange={(e) => setField({ dung_thi_thu: e.target.checked })} />
            Dùng cả cho Thi thử (để ghép vào đề)
          </label>
          <button type="submit" className="xbtn">{busy ? "AI đang soạn và soát lỗi… (có thể mất 1 phút)" : "Soạn với AI"}</button>
        </fieldset>
      </form>

      {error && <p role="alert" className="lv-alert">{error}</p>}
      {notice && <p role="status" className="lv-notice">{notice}</p>}

      {pending.length > 0 && (
        <div className="lv-ai__bar">
          <span>
            {pending.length} câu chờ duyệt · <b>{clean.length}</b> câu không có cảnh báo
          </span>
          <div className="lv-actions">
            {missingAudioCards.length > 0 && (
              <button type="button" className="xbtn xbtn--ghost xbtn--sm" onClick={() => fillMissingAudio(missingAudioCards)}
                disabled={audioBatchBusy}>
                <Icon name="spark" size={14} />{" "}
                {audioBatchBusy ? "Đang tạo giọng đọc AI…" : `Tạo giọng đọc AI (${missingAudioCards.length} câu Nghe)`}
              </button>
            )}
            <button type="button" className="xbtn" onClick={approveClean} disabled={!clean.length || clean.some((c) => c.busy)}>
              Duyệt tất cả câu sạch ({clean.length})
            </button>
          </div>
        </div>
      )}

      <ol className="lv-ai__list">
        {cards.map((card, index) => (
          <DraftCard key={card.key} card={card} number={index + 1} groups={groups} token={token}
            onMakeAudio={() => makeAudioForCard(card)}
            onApprove={() => approveOne(card)} onRecheck={() => recheck(card)} onAsk={(m) => ask(card, m)}
            onAccept={() => acceptProposal(card)} onRejectProposal={() => patchCard(card.key, { de_xuat: null })}
            onChange={(patch) => changeQuestion(card, patch)} onEdit={() => editByHand(card)}
            onRemove={() => setCards((list) => list.filter((c) => c.key !== card.key))} />
        ))}
      </ol>
    </section>
  );
}

function Warnings({ card }) {
  return (
    <>
      {card.loi && <p className="lv-alert">Chưa đủ thành phần: {card.loi}</p>}
      {card.van_de_ai === null || card.van_de_ai === undefined ? (
        <p className="lv-ai__warn">AI chưa soát câu này. Bấm “Kiểm tra lại” hoặc tự kiểm tra kỹ trước khi duyệt.</p>
      ) : card.van_de_ai.length > 0 ? (
        <div className="lv-ai__warn">
          <b>AI phát hiện:</b>
          <ul>{card.van_de_ai.map((v) => <li key={v}>{v}</li>)}</ul>
        </div>
      ) : (
        <p className="lv-ai__ok">AI soát: không phát hiện lỗi.</p>
      )}
      {card.trung_lap?.length > 0 && (
        <div className="lv-ai__warn">
          <b>Gần trùng câu đã có trong ngân hàng:</b>
          <ul>
            {card.trung_lap.map((t) => (
              <li key={t.id}>
                <Link className="xlink" to={`/giang-vien/cau-hoi/${t.id}`}>#{t.ma_goc_id}</Link> ({Math.round(t.do_giong * 100)}% giống,{" "}
                {t.trang_thai === "da_dang" ? "đang đăng" : "nháp"}): <span className="zh">{t.noi_dung}</span>
              </li>
            ))}
          </ul>
        </div>
      )}
      {card.luu_y?.map((w) => <p key={w} className="lv-hint">{w}</p>)}
    </>
  );
}

function DraftCard({ card, number, groups, token, onMakeAudio, onApprove, onRecheck, onAsk, onAccept, onRejectProposal, onChange, onEdit, onRemove }) {
  const [message, setMessage] = useState("");
  const q = card.cau_hoi;
  const [showImgBox, setShowImgBox] = useState(Boolean(q.tep_hinh || q.mo_ta_hinh || q.dang === "viet_mo"));
  const done = card.trang_thai === "da_duyet";

  async function makeImageForCard() {
    let desc = (q.mo_ta_hinh || "").trim();
    if (!desc) {
      const entered = window.prompt(
        "Nhập mô tả bức tranh minh họa cho câu này (tiếng Việt):",
        (q.dich_nghia || "").trim(),
      );
      if (entered === null) return null;
      desc = entered.trim();
    }
    if (desc.length < 2) throw new Error("Cần nhập mô tả bức tranh trước khi tạo hình AI");
    const data = await aiMakeImage(token, desc);
    onChange({ tep_hinh: data.duong_dan, mo_ta_hinh: q.mo_ta_hinh || desc });
    return data.duong_dan;
  }

  function send(e) {
    e.preventDefault();
    const text = message.trim();
    if (!text) return;
    setMessage("");
    onAsk(text);
  }

  if (done) {
    return (
      <li className="lv-ai__item lv-ai__item--done">
        <span>Câu {number}: đã duyệt và đăng.</span>
        <Link className="xlink" to={`/giang-vien/cau-hoi/${card.id}`}>Mở câu #{card.id}</Link>
      </li>
    );
  }

  return (
    <li className="lv-ai__item">
      <div className={card.de_xuat ? "lv-ai__compare" : undefined}>
        <div>
          {card.de_xuat && <p className="lv-ai__label">Bản hiện tại</p>}
          <QuestionPreview q={q} number={number} />
          <Warnings card={card} />
        </div>
        {card.de_xuat && (
          <div className="lv-ai__proposal">
            <p className="lv-ai__label">AI đề xuất</p>
            <QuestionPreview q={card.de_xuat.cau_hoi} number={number} />
            <Warnings card={card.de_xuat} />
            <div className="lv-actions">
              <button type="button" className="xbtn xbtn--sm" onClick={onAccept} disabled={card.busy}>Dùng bản này</button>
              <button type="button" className="xbtn xbtn--ghost xbtn--sm" onClick={onRejectProposal} disabled={card.busy}>Giữ bản cũ</button>
            </div>
          </div>
        )}
      </div>

      <div className="lv-ai__meta">
        {q.dang !== "ngu_lieu" && (
          <div className="lv-field">
            <label htmlFor={`${card.key}-group`}>Nhóm kiến thức</label>
            <select id={`${card.key}-group`} value={q.nhom_kien_thuc_id ?? ""} disabled={card.busy}
              onChange={(e) => onChange({ nhom_kien_thuc_id: e.target.value ? Number(e.target.value) : null })}>
              <option value="">Chưa gắn</option>
              {groups.map((g) => <option key={g.id} value={g.id}>{g.ten}</option>)}
            </select>
          </div>
        )}
        {q.ky_nang === "nghe" && (
          <MediaInput kind="audio" label="Âm thanh câu Nghe (bắt buộc để duyệt)" value={q.tep_audio} disabled={card.busy}
            onAiGenerate={onMakeAudio} aiLabel="Tạo giọng đọc AI"
            onChange={(v) => onChange({ tep_audio: v })} />
        )}
        {showImgBox ? (
          <div className="lv-field">
            <label htmlFor={`${card.key}-imgdesc`}>Mô tả hình minh họa (AI vẽ theo mô tả này)</label>
            <input id={`${card.key}-imgdesc`} value={q.mo_ta_hinh || ""} maxLength={1000} disabled={card.busy}
              placeholder="Ví dụ: Một cô gái đang mua táo ở quầy trái cây"
              onChange={(e) => onChange({ mo_ta_hinh: e.target.value || null })} />
            <MediaInput kind="hinh" label="" value={q.tep_hinh} disabled={card.busy}
              onAiGenerate={makeImageForCard} aiLabel="Tạo hình AI"
              onChange={(v) => onChange({ tep_hinh: v })} />
          </div>
        ) : (
          <button type="button" className="xlink" onClick={() => setShowImgBox(true)} disabled={card.busy}>
            + Thêm hình minh họa AI cho câu này
          </button>
        )}
      </div>

      <div className="lv-ai__chat" aria-label={`Trao đổi với AI về câu ${number}`}>
        {card.chat.map((m, i) => (
          <p key={i} className={m.vai_tro === "ai" ? "lv-ai__msg lv-ai__msg--ai" : "lv-ai__msg"}>
            <b>{m.vai_tro === "ai" ? "AI" : "Bạn"}:</b> {m.noi_dung}
          </p>
        ))}
        <form className="lv-ai__ask" onSubmit={send}>
          <input value={message} maxLength={1000} disabled={card.busy} aria-label="Nhắn cho AI"
            placeholder="Hỏi hoặc yêu cầu AI sửa, ví dụ: phương án B dễ quá, làm khó hơn"
            onChange={(e) => setMessage(e.target.value)} />
          <button type="submit" className="xbtn xbtn--ghost xbtn--sm" disabled={card.busy || !message.trim()}>
            {card.busy ? "Đang xử lý…" : "Gửi"}
          </button>
        </form>
      </div>

      {card.thong_bao && <p role="alert" className="lv-alert">{card.thong_bao}</p>}

      <div className="lv-actions">
        <button type="button" className="xbtn xbtn--sm" onClick={onApprove}
          disabled={card.busy || card.trang_thai !== "cho" || Boolean(card.loi) || needsAudio(q)}
          title={card.loi ? "Câu còn thiếu thành phần" : needsAudio(q) ? "Tải âm thanh thật trước khi duyệt" : undefined}>
          Duyệt và đăng
        </button>
        <button type="button" className="xbtn xbtn--ghost xbtn--sm" onClick={onRecheck} disabled={card.busy}>Kiểm tra lại</button>
        <button type="button" className="xbtn xbtn--ghost xbtn--sm" onClick={onEdit} disabled={card.busy}>Sửa tay</button>
        <button type="button" className="xbtn xbtn--danger xbtn--sm" onClick={onRemove} disabled={card.busy}>Bỏ</button>
        {card.trang_thai === "da_luu_nhap" && card.id && (
          <Link className="xlink" to={`/giang-vien/cau-hoi/${card.id}`}>Mở bản nháp #{card.id}</Link>
        )}
      </div>
    </li>
  );
}
