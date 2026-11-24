// Thành phần hiển thị câu hỏi, phương án và thẻ từ dùng chung cho Ôn luyện, Học thử, Vượt thửa và Sổ tay.
import { useEffect, useState } from "react";

import HanziText from "./HanziText.jsx";
import Icon from "./Icon.jsx";
import { pronounceUrl } from "../../features/search/api/searchApi.js";
import { mediaUrl, splitOption } from "../utils/format.js";

export const SKILL = { nghe: "Nghe", doc: "Đọc", viet: "Viết", tu_vung: "Từ vựng" };
export const CHOICE = ["chon_mot", "dung_sai", "chon_bo_chung"];
export const LATIN = /[A-Za-zÀ-ỹ]/;

export function instruction(q, skill) {
  if (q.dang === "dung_sai") return "Đúng hay sai?";
  if (q.dang === "dien_chu") return "Điền vào chỗ trống";
  if (q.dang === "sap_xep") return "Sắp xếp thành câu đúng";
  if (q.dang === "dich_cau") return "Dịch sang tiếng Trung";
  if (skill === "tu_vung") return LATIN.test(q.noi_dung || "") ? "Chọn từ đúng" : "Chọn nghĩa của từ";
  if (skill === "nghe") return "Nghe và chọn đáp án đúng";
  return "Chọn đáp án đúng";
}

// Trích xuất mảng tin nhắn từ tham số gọi lại của XiangChat
export function pickMessages(args) {
  for (const a of args) {
    if (Array.isArray(a)) return a;
    if (a && typeof a === "object" && Array.isArray(a.tin_nhan)) return a.tin_nhan;
  }
  return [];
}

export function Option({ option }) {
  const { text, pinyin } = splitOption(option.noi_dung);
  return (
    <>
      {option.tep_hinh && <img src={mediaUrl(option.tep_hinh)} alt="" />}
      {text && (LATIN.test(text) && !pinyin ? <span>{text}</span> : <HanziText text={text} pinyin={pinyin} />)}
    </>
  );
}

export function FlashCards({ words, onDone, returnLabel = "Làm câu hỏi" }) {
  const [i, setI] = useState(0);
  const [flip, setFlip] = useState(false);
  const w = words[i];

  function speakWord(text, audioPath = null) {
    if (!text && !audioPath) return;
    try {
      const src = audioPath ? mediaUrl(audioPath) : pronounceUrl(text);
      new Audio(src).play().catch(() => {});
    } catch {
      /* trình duyệt chặn tự phát */
    }
  }

  useEffect(() => {
    function onKey(e) {
      if (["INPUT", "TEXTAREA"].includes(e.target.tagName)) return;
      if (e.key === " ") {
        e.preventDefault();
        setFlip((f) => !f);
      } else if (e.key === "ArrowLeft" && i > 0) {
        setI(i - 1);
        setFlip(false);
      } else if (e.key === "ArrowRight" && i < words.length - 1) {
        setI(i + 1);
        setFlip(false);
      } else if (e.key === "Escape") {
        onDone();
      }
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [i, words.length, onDone]);

  return (
    <div className="sl-cards">
      <p className="sl-meta">Thẻ từ {i + 1}/{words.length} · bấm thẻ hoặc phím Cách để lật</p>
      <button type="button" className={`sl-card${flip ? " is-flipped" : ""}`} onClick={() => setFlip(!flip)} aria-label={flip ? "Mặt trước" : "Lật thẻ"}>
        <span className="sl-card__front hz">{w.chu_han}</span>
        <span className="sl-card__back">
          <b className="hz">{w.chu_han}</b><em>{w.pinyin}</em><span>{w.nghia}</span>
          {w.vd_cau && <small><span className="hz">{w.vd_cau}</span>{w.vd_nghia && ` – ${w.vd_nghia}`}</small>}
        </span>
      </button>
      <div className="sl-cards__nav">
        <button type="button" className="xc-btn xc-btn--plain xc-btn--sm" disabled={i === 0} onClick={() => { setI(i - 1); setFlip(false); }}>Trước</button>
        <button type="button" className="xc-btn xc-btn--plain xc-btn--sm" onClick={() => speakWord(w.chu_han)}>
          <Icon name="audio" size={16} /> Nghe từ
        </button>
        {i < words.length - 1
          ? <button type="button" className="xc-btn xc-btn--plain xc-btn--sm" onClick={() => { setI(i + 1); setFlip(false); }}>Thẻ sau</button>
          : null}
        <button type="button" className="xc-btn xc-btn--sm" onClick={onDone}>{returnLabel}</button>
      </div>
      <p className="sl-note">Xem thẻ không tốn năng lượng — bạn có thể mở lại Thẻ từ bất cứ lúc nào trong bài học.</p>
    </div>
  );
}
