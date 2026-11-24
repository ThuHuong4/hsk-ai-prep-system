import { DANG_LABELS, mediaUrl, optionLetter } from "../utils/labels.js";

function Media({ q, hideAudio = false }) {
  return (
    <>
      {q.tep_hinh && <img className="lv-preview__img" src={mediaUrl(q.tep_hinh)} alt={q.mo_ta_hinh || ""} />}
      {!hideAudio && q.tep_audio && <audio controls preload="none" src={mediaUrl(q.tep_audio)} />}
    </>
  );
}

function Options({ options, correctIndex }) {
  if (!options?.length) return null;
  return (
    <ol className="lv-preview__options">
      {options.map((o, i) => (
        <li key={i} className={o.la_dap_an_dung || correctIndex === i + 1 ? "is-correct" : undefined}>
          <strong>{optionLetter(i)}.</strong> {o.noi_dung && <span className="zh">{o.noi_dung}</span>}
          {o.tep_hinh && <img src={mediaUrl(o.tep_hinh)} alt={`Phương án ${optionLetter(i)}`} />}
        </li>
      ))}
    </ol>
  );
}

// Hiển thị một câu (hoặc câu con) kèm đáp án để Giảng viên soát lại
export function AnswerLine({ q }) {
  if (q.dang === "chon_bo_chung") {
    return <p className="lv-preview__answer">Đáp án: {q.dap_an_thu_tu ? optionLetter(q.dap_an_thu_tu - 1) : "—"}</p>;
  }
  if (q.dang === "sap_xep" || q.dang === "dien_chu") {
    return <p className="lv-preview__answer">Đáp án chấp nhận: <span className="zh">{(q.dap_an_chap_nhan || []).join(" | ")}</span></p>;
  }
  if (q.dang === "viet_mo" || q.dang === "dich_cau") {
    return (
      <p className="lv-preview__answer">
        Điểm tối đa {q.diem_toi_da}, ngưỡng đạt {q.nguong_dat}
        {q.tu_bat_buoc && <> · Từ bắt buộc: <span className="zh">{q.tu_bat_buoc}</span></>}
        {q.dang === "dich_cau" && q.dap_an_chap_nhan?.length > 0 && <> · Bản dịch mẫu: {q.dap_an_chap_nhan.join(" | ")}</>}
      </p>
    );
  }
  return null;
}

export default function QuestionPreview({ q, number, hideAudio = false }) {
  return (
    <div className="lv-preview">
      <p className="lv-preview__head">
        {number && <strong>Câu {number}. </strong>}
        <span className="lv-muted">{DANG_LABELS[q.dang]}</span>
      </p>
      {q.noi_dung && <p className="zh lv-preview__text">{q.noi_dung}</p>}
      <Media q={q} hideAudio={hideAudio} />
      {q.loi_nghe && <p className="lv-preview__note">Lời nghe: <span className="zh">{q.loi_nghe}</span></p>}
      {q.dang !== "chon_bo_chung" && <Options options={q.phuong_an} />}
      <AnswerLine q={q} />
      {q.giai_thich && <p className="lv-preview__note">Giải thích: {q.giai_thich}</p>}
      {q.goi_y && <p className="lv-preview__note">Gợi ý 1: {q.goi_y}</p>}
      {q.goi_y_2 && <p className="lv-preview__note">Gợi ý 2: {q.goi_y_2}</p>}
    </div>
  );
}

export function SharedPassage({ q, hideAudio = false }) {
  return (
    <div className="lv-preview lv-preview--passage">
      <p className="lv-preview__head"><span className="lv-muted">Ngữ liệu chung</span></p>
      {q.noi_dung && <p className="zh lv-preview__text">{q.noi_dung}</p>}
      <Media q={q} hideAudio={hideAudio} />
      <Options options={q.phuong_an} />
    </div>
  );
}
