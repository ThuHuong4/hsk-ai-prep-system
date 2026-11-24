import { useEffect, useMemo, useRef, useState } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";

import { useAuth } from "../../auth/context/AuthContext.jsx";
import {
  aiApprovePart,
  aiChatPart,
  aiCreateExam,
  aiGeneratePart,
  aiMakeAudio,
  aiMakeImage,
  getExamBlueprint,
  uploadMedia,
} from "../api/lecturerApi.js";
import AiPartCard from "../components/AiPartCard.jsx";
import Icon from "../../../shared/components/Icon.jsx";
import { useLevels } from "../hooks/useLevels.js";
import {
  canCheck,
  clearDraft,
  loadDraft,
  mediaSlots,
  missingMedia,
  newKey,
  runPool,
  saveDraft,
  setAt,
  slotId,
  summary,
} from "../utils/aiExamParts.js";
import "../styles/lecturer.css";
import "../styles/aiExam.css";

/**
 * Soạn đề thi thử MỚI với AI theo từng phần, đúng cấu trúc HSK 2.0:
 * AI soạn nội dung + tạo hình + giọng đọc -> Giảng viên xem, nghe, trao đổi với AI, sửa
 * -> Giảng viên duyệt từng phần (câu được lưu vào ngân hàng, ghi người duyệt) -> tạo đề nháp -> Đăng.
 */
const KIND_LABEL = {
  nghe_tranh_dung_sai: "Nghe – tranh Đúng/Sai",
  nghe_chon_tranh: "Nghe – chọn tranh",
  nghe_noi_tranh: "Nghe – nối tranh A–F",
  nghe_chon_chu: "Nghe – chọn đáp án",
  nghe_phan_doan: "Nghe – phán đoán ★",
  nghe_doan_2cau: "Nghe – đoạn 2 câu hỏi",
  doc_tranh_tu: "Đọc – tranh và từ",
  doc_noi_tranh: "Đọc – nối tranh A–F",
  doc_ghep_cau: "Đọc – ghép câu A–F",
  doc_chon_tu: "Đọc – chọn từ điền",
  doc_phan_doan: "Đọc – phán đoán ★",
  doc_doan_chon: "Đọc – đoạn văn chọn đáp án",
  doc_doan_2cau: "Đọc – đoạn 2 câu hỏi",
  doc_sap_xep_doan: "Đọc – sắp xếp 3 câu",
  viet_sap_xep: "Viết – sắp xếp thành câu",
  viet_dien_chu: "Viết – viết chữ theo pinyin",
  viet_tranh: "Viết – xem tranh viết câu",
};
const EMPTY = { parts: {}, info: { ten: "", ma_de: "", thoi_luong_phut: "" }, chu_de: "", yeu_cau: "" };

const toCard = (the) => ({ ...the, key: newKey(), da_kiem_tra: false, duyet: null, loi_duyet: null });

export default function AiExamBuilderPage() {
  const { token } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const levels = useLevels();
  const [levelId, setLevelId] = useState(null);
  const [blue, setBlue] = useState(null);
  const [draft, setDraft] = useState(EMPTY);
  const [active, setActive] = useState(1);
  const [media, setMedia] = useState({});
  const [busy, setBusy] = useState("");
  const [error, setError] = useState("");
  const [note, setNote] = useState("");
  const [message, setMessage] = useState("");
  const draftRef = useRef(draft);
  draftRef.current = draft;

  // ---------------------------------------------------------------- cấp độ & cấu trúc
  useEffect(() => {
    if (!levelId && levels.length) setLevelId(location.state?.cap_do_id ?? levels[0].ma_cap_do);
  }, [levels]); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    if (!levelId || !token) return undefined;
    const ctrl = new AbortController();
    setBlue(null);
    setError("");
    getExamBlueprint(token, levelId, ctrl.signal)
      .then((data) => {
        setBlue(data);
        const saved = loadDraft(levelId);
        setDraft(saved || { ...EMPTY, info: { ten: `Đề thi thử ${data.cap} – soạn với AI`, ma_de: "", thoi_luong_phut: data.thoi_luong_phut } });
        setActive(data.phan[0]?.phan || 1);
        setMedia({});
      })
      .catch((err) => {
        if (err.name !== "AbortError") setError(err?.message || "Không tải được cấu trúc đề");
      });
    return () => ctrl.abort();
  }, [levelId, token]);

  useEffect(() => {
    if (blue && levelId) saveDraft(levelId, draft);
  }, [draft, blue, levelId]);

  const part = blue?.phan.find((p) => p.phan === active);
  const partState = draft.parts[active] || { cards: [], chat: [] };

  // Số thứ tự câu bắt đầu của từng phần (đánh số liên tục cả đề như đề thật)
  const starts = useMemo(() => {
    const map = {};
    let n = 1;
    (blue?.phan || []).forEach((p) => { map[p.phan] = n; n += p.so_cau; });
    return map;
  }, [blue]);

  // ---------------------------------------------------------------- cập nhật state
  function updatePart(phan, fn) {
    setDraft((d) => {
      const cur = d.parts[phan] || { cards: [], chat: [] };
      return { ...d, parts: { ...d.parts, [phan]: fn(cur) } };
    });
  }
  const updateCards = (phan, fn) => updatePart(phan, (p) => ({ ...p, cards: fn(p.cards) }));
  const patchCard = (phan, key, fn) => updateCards(phan, (cards) => cards.map((c) => (c.key === key ? fn(c) : c)));

  function findCard(phan, key) {
    return (draftRef.current.parts[phan]?.cards || []).find((c) => c.key === key);
  }

  // Cụm theo thứ tự đoạn trong cấu trúc, để đánh số và ghép đề đúng thứ tự đề thật
  function ordered(p, cards) {
    const order = p.doan.map((s) => s.kieu);
    return [...cards].sort((a, b) => order.indexOf(a.muc.kieu) - order.indexOf(b.muc.kieu));
  }

  // ---------------------------------------------------------------- tạo tệp (hình / âm thanh)
  async function makeSlot(phan, key, path) {
    const card = findCard(phan, key);
    if (!card) return;
    const slot = mediaSlots(card.muc).find((s) => slotId(s.path) === slotId(path));
    if (!slot) return;
    const sid = slotId(path);
    setMedia((m) => ({ ...m, [key]: { ...(m[key] || {}), [sid]: "dang" } }));
    try {
      const data = slot.loai === "hinh"
        ? await aiMakeImage(token, slot.nguon || "")
        : await aiMakeAudio(token, Number(levelId), slot.nguon || "");
      patchCard(phan, key, (c) => ({ ...c, muc: setAt(c.muc, path, data.duong_dan), da_kiem_tra: false }));
      setMedia((m) => ({ ...m, [key]: { ...(m[key] || {}), [sid]: undefined } }));
    } catch (err) {
      setMedia((m) => ({ ...m, [key]: { ...(m[key] || {}), [sid]: err?.message || "Tạo tệp thất bại" } }));
    }
  }

  async function uploadSlot(phan, key, path, file) {
    const card = findCard(phan, key);
    const slot = card && mediaSlots(card.muc).find((s) => slotId(s.path) === slotId(path));
    if (!slot) return;
    const sid = slotId(path);
    setMedia((m) => ({ ...m, [key]: { ...(m[key] || {}), [sid]: "dang" } }));
    try {
      const data = await uploadMedia(token, slot.loai === "hinh" ? "hinh" : "audio", file);
      patchCard(phan, key, (c) => ({ ...c, muc: setAt(c.muc, path, data.duong_dan), da_kiem_tra: false }));
      setMedia((m) => ({ ...m, [key]: { ...(m[key] || {}), [sid]: undefined } }));
    } catch (err) {
      setMedia((m) => ({ ...m, [key]: { ...(m[key] || {}), [sid]: err?.message || "Tải tệp thất bại" } }));
    }
  }

  // Tạo mọi tệp còn thiếu của các thẻ (tối đa 3 tệp cùng lúc)
  function fillMedia(phan, cards) {
    const tasks = [];
    cards.forEach((c) => missingMedia(c.muc).forEach((s) => tasks.push(() => makeSlot(phan, c.key, s.path))));
    if (tasks.length) runPool(tasks, 3);
  }

  // ---------------------------------------------------------------- AI soạn
  function others(phan, exceptKey) {
    return (draftRef.current.parts[phan]?.cards || []).filter((c) => c.key !== exceptKey).map((c) => summary(c.muc));
  }

  async function generate(p, opts = {}) {
    setBusy(opts.label || "Đang soạn");
    setError("");
    setNote("");
    try {
      const data = await aiGeneratePart(token, {
        cap_do_id: Number(levelId), phan: p.phan, kieu: opts.kieu || null, so_muc: opts.so_muc || null,
        chu_de: draft.chu_de.trim() || null, yeu_cau: draft.yeu_cau.trim() || null,
        tranh: others(p.phan, opts.replaceKey).slice(0, 40),
      });
      const cards = (data.the || []).map(toCard);
      if (opts.replaceKey) {
        updateCards(p.phan, (list) => list.flatMap((c) => (c.key === opts.replaceKey ? cards.slice(0, 1) : [c])));
        fillMedia(p.phan, cards.slice(0, 1));
      } else {
        updateCards(p.phan, (list) => [...(opts.fresh ? list.filter((c) => c.duyet) : list), ...cards]);
        fillMedia(p.phan, cards);
      }
      if (data.ghi_chu) setNote(data.ghi_chu);
    } catch (err) {
      setError(err?.message || "AI chưa soạn được, vui lòng thử lại");
    } finally {
      setBusy("");
    }
  }

  // Soạn cả phần: giữ mục đã duyệt, soạn bù phần còn thiếu của từng kiểu câu
  async function generateAll(p) {
    const keep = (draftRef.current.parts[p.phan]?.cards || []).filter((c) => c.duyet);
    if (!keep.length) {
      await generate(p, { fresh: true, label: "AI đang soạn cả phần" });
      return;
    }
    updateCards(p.phan, () => keep);
    for (const seg of p.doan) {
      const lack = seg.so_muc - keep.filter((c) => c.muc.kieu === seg.kieu).length;
      if (lack > 0) await generate(p, { kieu: seg.kieu, so_muc: lack, label: "AI đang soạn bù" }); // eslint-disable-line no-await-in-loop
    }
  }

  // ---------------------------------------------------------------- trao đổi với AI
  async function sendChat(e) {
    e.preventDefault();
    const text = message.trim();
    const open = ordered(part, partState.cards).filter((c) => !c.duyet);
    if (!text || !open.length) return;
    setMessage("");
    setBusy("AI đang trả lời");
    setError("");
    const history = partState.chat;
    updatePart(active, (p) => ({ ...p, chat: [...history, { vai_tro: "gv", noi_dung: text }] }));
    try {
      const data = await aiChatPart(token, {
        cap_do_id: Number(levelId), phan: active, muc: open.map((c) => c.muc), tin_nhan: text, lich_su: history.slice(-10),
      });
      const changed = [];
      (data.sua || []).forEach(({ stt, the }) => {
        const target = open[stt - 1];
        if (target) changed.push({ ...toCard(the), key: target.key });
      });
      updatePart(active, (p) => ({
        ...p,
        chat: [...history, { vai_tro: "gv", noi_dung: text },
          { vai_tro: "ai", noi_dung: data.tra_loi + (changed.length ? ` (Đã sửa ${changed.length} mục, xem lại các mục đánh dấu “AI vừa sửa”.)` : "") }],
        cards: p.cards.map((c) => changed.find((x) => x.key === c.key) ? { ...changed.find((x) => x.key === c.key), vua_sua: true } : c),
      }));
      fillMedia(active, changed);
    } catch (err) {
      updatePart(active, (p) => ({ ...p, chat: history }));
      setError(err?.message || "AI chưa trả lời được, vui lòng thử lại");
    } finally {
      setBusy("");
    }
  }

  // ---------------------------------------------------------------- duyệt phần
  const ready = partState.cards.filter((c) => !c.duyet && c.da_kiem_tra && canCheck(c));

  async function approve() {
    if (!ready.length) return;
    setBusy("Đang lưu và đăng câu");
    setError("");
    try {
      const data = await aiApprovePart(token, {
        cap_do_id: Number(levelId), phan: active, muc: ready.map((c) => c.muc), da_kiem_tra: true,
      });
      const byKey = {};
      (data.ket_qua || []).forEach((r) => { byKey[ready[r.stt - 1]?.key] = r; });
      updateCards(active, (cards) => cards.map((c) => {
        const r = byKey[c.key];
        if (!r) return c;
        return r.loi ? { ...c, loi_duyet: r.loi, da_kiem_tra: false } : { ...c, duyet: { id: r.id, cau_ids: r.cau_ids }, loi_duyet: null, vua_sua: false };
      }));
      const failed = (data.ket_qua || []).filter((r) => r.loi).length;
      setNote(failed ? `Có ${failed} mục chưa duyệt được, xem lỗi ở từng mục.` : "Đã duyệt: câu đã lưu vào ngân hàng và đăng (nguồn “Soạn với AI”).");
    } catch (err) {
      setError(err?.message || "Không duyệt được");
    } finally {
      setBusy("");
    }
  }

  // ---------------------------------------------------------------- tạo đề nháp
  const progress = (blue?.phan || []).map((p) => {
    const cards = draft.parts[p.phan]?.cards || [];
    const done = cards.filter((c) => c.duyet).reduce((n, c) => n + c.duyet.cau_ids.length, 0);
    return { ...p, done };
  });
  const totalDone = progress.reduce((n, p) => n + p.done, 0);
  const totalNeed = progress.reduce((n, p) => n + p.so_cau, 0);
  const info = draft.info;
  const canCreate = totalDone > 0 && info.ten.trim() && info.ma_de.trim().length >= 2 && !busy;

  async function createExam() {
    setBusy("Đang tạo đề nháp");
    setError("");
    const items = [];
    blue.phan.forEach((p) => {
      ordered(p, draft.parts[p.phan]?.cards || []).filter((c) => c.duyet)
        .forEach((c) => c.duyet.cau_ids.forEach((id) => items.push({ cau_hoi_id: id, phan: p.phan, la_cau_vi_du: false })));
    });
    try {
      const data = await aiCreateExam(token, {
        thong_tin: {
          cap_do_id: Number(levelId), ten: info.ten.trim(), ma_de: info.ma_de.trim(),
          nguon: "Soạn với AI theo cấu trúc HSK 2.0, giảng viên duyệt từng phần",
          thoi_luong_phut: Number(info.thoi_luong_phut) || null, tep_audio_chung: null,
        },
        cau_hoi: items,
      });
      clearDraft(levelId);
      navigate(`/giang-vien/bo-de/${data.id}`);
    } catch (err) {
      setError(err?.message || "Không tạo được đề");
      setBusy("");
    }
  }

  function resetLevel() {
    if (!window.confirm("Bỏ toàn bộ bản đang soạn của cấp này? Câu đã duyệt vẫn còn trong ngân hàng.")) return;
    clearDraft(levelId);
    setDraft({ ...EMPTY, info: { ten: `Đề thi thử ${blue.cap} – soạn với AI`, ma_de: "", thoi_luong_phut: blue.thoi_luong_phut } });
    setMedia({});
  }

  // ---------------------------------------------------------------- giao diện
  const ok = blue?.san_sang;
  let counter = part ? starts[part.phan] : 1;

  return (
    <section className="lv-page">
      <Link to="/giang-vien/bo-de/ai" className="lv-back"><Icon name="back" size={18} /> Tạo đề với AI</Link>
      <div className="lv-page__head">
        <div className="lv-page__intro">
          <h1>Soạn đề với AI theo từng phần</h1>
          <p>
            AI soạn câu mới theo đúng cấu trúc đề HSK 2.0, tự tạo hình và giọng đọc. Bạn soạn và duyệt <b>từng phần</b>:
            xem hình, nghe âm thanh, trao đổi với AI để sửa, rồi bấm Duyệt. Đủ các phần thì tạo đề nháp.
          </p>
        </div>
        <Link className="xbtn xbtn--ghost" to="/giang-vien/bo-de/ai-ngan-hang"><Icon name="layers" /> Ghép từ câu đã duyệt</Link>
      </div>

      <div className="lv-card ae-top">
        <div className="lv-grid-3">
          <div className="lv-field">
            <label htmlFor="ae-level">Cấp độ</label>
            <select id="ae-level" value={levelId || ""} disabled={Boolean(busy)} onChange={(e) => setLevelId(Number(e.target.value))}>
              {levels.map((l) => <option key={l.ma_cap_do} value={l.ma_cap_do}>{l.ten_cap_do}</option>)}
            </select>
          </div>
          <div className="lv-field">
            <label htmlFor="ae-topic">Chủ đề chung (không bắt buộc)</label>
            <input id="ae-topic" maxLength={200} value={draft.chu_de} placeholder="Để trống = AI chọn đa dạng"
              onChange={(e) => setDraft((d) => ({ ...d, chu_de: e.target.value }))} />
          </div>
          <div className="lv-field">
            <label htmlFor="ae-req">Yêu cầu thêm cho AI</label>
            <input id="ae-req" maxLength={1000} value={draft.yeu_cau} placeholder="Ví dụ: tránh chủ đề đã dùng ở đề trước"
              onChange={(e) => setDraft((d) => ({ ...d, yeu_cau: e.target.value }))} />
          </div>
        </div>
        {ok && !ok.ai && <p className="lv-alert">Chưa cấu hình AI (OPENAI_API_KEY, OPENAI_MODEL trong .env).</p>}
        {ok && !ok.giong_doc && <p className="lv-ai__warn">Chưa cấu hình giọng đọc (OPENAI_TTS_MODEL): câu Nghe phải tự tải tệp âm thanh.</p>}
        {ok && !ok.tao_hinh && <p className="lv-ai__warn">Chưa cấu hình tạo hình (OPENAI_IMAGE_MODEL): câu có tranh phải tự tải hình.</p>}
      </div>

      {error && <p role="alert" className="lv-alert">{error}</p>}
      {note && <p className="lv-ai__ok" role="status">{note}</p>}
      {!blue && !error && <p className="lv-help">Đang tải cấu trúc đề…</p>}

      {blue && (
        <div className="ae-layout">
          <nav className="ae-parts" aria-label="Các phần của đề">
            <p className="lv-ai__label">{blue.cap} · {totalNeed} câu · {blue.thoi_luong_phut} phút</p>
            {progress.map((p) => (
              <button key={p.phan} type="button" disabled={Boolean(busy)}
                className={`ae-part${p.phan === active ? " is-active" : ""}${p.done >= p.so_cau ? " is-done" : ""}`}
                onClick={() => { setActive(p.phan); setNote(""); }}>
                <span className="zh">{p.ten}</span>
                <small>{p.mo_ta}</small>
                <b>{p.done}/{p.so_cau} câu đã duyệt</b>
              </button>
            ))}
            <button type="button" className="xlink ae-reset" onClick={resetLevel} disabled={Boolean(busy)}>Bỏ bản đang soạn</button>
          </nav>

          <div className="ae-main">
            {part && (
              <section className="lv-card" aria-label={part.ten}>
                <div className="ae-part__head">
                  <div>
                    <h2 className="lv-ai__title"><span className="zh">{part.ten}</span> · Câu {starts[part.phan]}–{starts[part.phan] + part.so_cau - 1}</h2>
                    <p className="lv-help">{part.mo_ta}. {blue.phat_nghe > 1 && part.ky_nang === "nghe" ? "Âm thanh đọc 2 lần như đề thật." : ""}</p>
                  </div>
                  <button type="button" className="xbtn" disabled={Boolean(busy) || (ok && !ok.ai)} onClick={() => generateAll(part)}>
                    <Icon name="spark" /> {partState.cards.length ? "Soạn lại cả phần" : "Soạn phần này với AI"}
                  </button>
                </div>
                {busy && <p className="ae-busy" role="status">{busy}… (có thể mất 30–90 giây)</p>}

                {part.doan.map((seg) => {
                  const cards = ordered(part, partState.cards).filter((c) => c.muc.kieu === seg.kieu);
                  const lack = seg.so_muc - cards.length;
                  return (
                    <div key={seg.kieu} className="ae-seg">
                      {part.doan.length > 1 && <h3>{KIND_LABEL[seg.kieu]} · {seg.so_cau} câu</h3>}
                      <ol className="ae-list">
                        {cards.map((c) => {
                          const from = counter;
                          counter += c.so_cau;
                          return (
                            <AiPartCard key={c.key} card={c} from={from} label={`${KIND_LABEL[c.muc.kieu]}${c.vua_sua ? " · AI vừa sửa" : ""}`}
                              media={media[c.key] || {}} busy={Boolean(busy)}
                              onRegen={(path) => makeSlot(part.phan, c.key, path)}
                              onUpload={(path, file) => uploadSlot(part.phan, c.key, path, file)}
                              onToggle={() => patchCard(part.phan, c.key, (x) => ({ ...x, da_kiem_tra: !x.da_kiem_tra }))}
                              onRemove={() => updateCards(part.phan, (list) => list.filter((x) => x.key !== c.key))}
                              onRedo={() => generate(part, { kieu: c.muc.kieu, so_muc: 1, replaceKey: c.key, label: "AI đang soạn lại mục" })} />
                          );
                        })}
                      </ol>
                      {partState.cards.length > 0 && lack > 0 && (
                        <button type="button" className="xbtn xbtn--ghost" disabled={Boolean(busy)}
                          onClick={() => generate(part, { kieu: seg.kieu, so_muc: lack, label: "AI đang soạn thêm" })}>
                          <Icon name="plus" /> Soạn thêm {lack} mục còn thiếu
                        </button>
                      )}
                      {lack < 0 && <p className="lv-ai__warn">Nhiều hơn cấu trúc đề {-lack} mục; bỏ bớt cho đúng số câu.</p>}
                    </div>
                  );
                })}

                {partState.cards.some((c) => !c.duyet) && (
                  <section className="ae-chat" aria-label="Trao đổi với AI về phần này">
                    <h3 className="lv-ai__title">Trao đổi với AI về phần này</h3>
                    {partState.chat.length > 0 && (
                      <div className="lv-ai__chat">
                        {partState.chat.map((m, i) => (
                          <p key={i} className={m.vai_tro === "ai" ? "lv-ai__msg lv-ai__msg--ai" : "lv-ai__msg"}>
                            <b>{m.vai_tro === "ai" ? "AI" : "Bạn"}:</b> {m.noi_dung}
                          </p>
                        ))}
                      </div>
                    )}
                    <form className="lv-ai__ask" onSubmit={sendChat}>
                      <input value={message} maxLength={1000} disabled={Boolean(busy)} aria-label="Nhắn cho AI về phần này"
                        placeholder="Ví dụ: câu 3 hai phương án B, C đều đúng; đổi câu 5 sang chủ đề mua sắm"
                        onChange={(e) => setMessage(e.target.value)} />
                      <button type="submit" className="xbtn xbtn--sm" disabled={Boolean(busy) || !message.trim()}>Gửi</button>
                    </form>
                    <p className="lv-help">AI chỉ đề xuất bản sửa; mục được sửa phải xem lại và tích kiểm tra lần nữa.</p>
                  </section>
                )}

                {partState.cards.some((c) => !c.duyet) && (
                  <div className="ae-approve">
                    <button type="button" className="xbtn" onClick={approve} disabled={Boolean(busy) || !ready.length}>
                      <Icon name="check" /> Duyệt {ready.length} mục đã kiểm tra
                    </button>
                    <span className="lv-help">Chỉ mục đã đủ hình, âm thanh và được tích “đã kiểm tra” mới duyệt được.</span>
                  </div>
                )}
              </section>
            )}

            <section className="lv-card" aria-label="Tạo đề nháp">
              <h2 className="lv-ai__title">Tạo đề nháp</h2>
              <p className="lv-help">Đã duyệt {totalDone}/{totalNeed} câu.{totalDone < totalNeed ? " Đề chưa đủ cấu trúc vẫn tạo được nháp, nhưng nên duyệt đủ các phần trước khi Đăng." : ""}</p>
              <div className="lv-grid-3">
                <div className="lv-field">
                  <label htmlFor="ae-name">Tên đề</label>
                  <input id="ae-name" maxLength={150} value={info.ten}
                    onChange={(e) => setDraft((d) => ({ ...d, info: { ...d.info, ten: e.target.value } }))} />
                </div>
                <div className="lv-field">
                  <label htmlFor="ae-code">Mã đề</label>
                  <input id="ae-code" maxLength={30} value={info.ma_de} placeholder="Ví dụ: H1_AI_01"
                    onChange={(e) => setDraft((d) => ({ ...d, info: { ...d.info, ma_de: e.target.value } }))} />
                </div>
                <div className="lv-field">
                  <label htmlFor="ae-time">Thời lượng (phút)</label>
                  <input id="ae-time" type="number" min={1} max={300} value={info.thoi_luong_phut}
                    onChange={(e) => setDraft((d) => ({ ...d, info: { ...d.info, thoi_luong_phut: e.target.value } }))} />
                </div>
              </div>
              <div className="lv-actions">
                <button type="button" className="xbtn" onClick={createExam} disabled={!canCreate}>Tạo đề nháp ({totalDone} câu)</button>
                <span className="lv-help">Đề tạo ra ở trạng thái nháp; bạn mở đề kiểm tra lần cuối rồi bấm Đăng.</span>
              </div>
            </section>
          </div>
        </div>
      )}
    </section>
  );
}
