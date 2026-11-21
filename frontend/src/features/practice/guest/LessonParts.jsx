// Phần hiển thị dùng cho màn học thử của Khách (giống màn làm bài của Học viên)
import { useState } from "react";

import { mediaUrl } from "../../lecturer/utils/labels.js";
import HanziText from "../../mock_test/components/HanziText.jsx";
import { splitOption } from "../../mock_test/utils/paper.js";

export const SKILL = { nghe: "Nghe", doc: "Đọc", viet: "Viết", tu_vung: "Từ vựng" };
export const CHOICE = ["chon_mot", "dung_sai", "chon_bo_chung"];
export const LATIN = /[A-Za-zÀ-ỹ]/;

export function instruction(q, skill) {
  if (q.dang === "dung_sai") return "Đúng hay sai?";
  if (q.dang === "dien_chu") return "Điền vào chỗ trống";
  if (q.dang === "sap_xep") return "Sắp xếp thành câu đúng";
  if (skill === "tu_vung") return LATIN.test(q.noi_dung || "") ? "Chọn từ đúng" : "Chọn nghĩa của từ";
  if (skill === "nghe") return "Nghe và chọn đáp án đúng";
  return "Chọn đáp án đúng";
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

export function FlashCards({ words, onDone }) {
  const [i, setI] = useState(0);
  const [flip, setFlip] = useState(false);
  const w = words[i];
  return (
    <div className="sl-cards">
      <p className="sl-meta">Thẻ từ {i + 1}/{words.length} · bấm thẻ để lật</p>
      <button type="button" className={`sl-card${flip ? " is-flipped" : ""}`} onClick={() => setFlip(!flip)} aria-label={flip ? "Mặt trước" : "Lật thẻ"}>
        <span className="sl-card__front hz">{w.chu_han}</span>
        <span className="sl-card__back">
          <b className="hz">{w.chu_han}</b><em>{w.pinyin}</em><span>{w.nghia}</span>
          {w.vd_cau && <small><span className="hz">{w.vd_cau}</span>{w.vd_nghia && ` – ${w.vd_nghia}`}</small>}
        </span>
      </button>
      <div className="sl-cards__nav">
        <button type="button" className="xc-btn xc-btn--plain xc-btn--sm" disabled={i === 0} onClick={() => { setI(i - 1); setFlip(false); }}>Trước</button>
        {i < words.length - 1
          ? <button type="button" className="xc-btn xc-btn--plain xc-btn--sm" onClick={() => { setI(i + 1); setFlip(false); }}>Thẻ sau</button>
          : null}
        <button type="button" className="xc-btn xc-btn--sm" onClick={onDone}>Làm câu hỏi</button>
      </div>
      <p className="sl-note">Xem thẻ không tốn năng lượng và không tính hoàn thành bài.</p>
    </div>
  );
}
