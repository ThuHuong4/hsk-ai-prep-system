import { useEffect, useState } from "react";

import { mediaUrl } from "../../lecturer/utils/labels.js";
import { LETTERS, splitOption } from "../utils/paper.js";
import SentenceBuilder from "../../../shared/components/SentenceBuilder.jsx";
import HanziText from "./HanziText.jsx";
import XiangChat from "../../ai_tutor/components/XiangChat.jsx";
// Đề thi trình bày như đề giấy. mode = "do" (đang làm) | "review" (xem lại sau khi nộp)

function choiceState(mode, item, optionId) {
  const chosen = item.tra_loi?.phuong_an_chon_id === optionId;
  if (item.la_cau_vi_du) return item.cau_hoi.dap_an_id === optionId ? " is-example" : "";
  if (mode === "do") return chosen ? " is-selected" : "";
  const correct = item.cau_hoi.dap_an_id === optionId;
  if (correct) return chosen ? " is-correct is-selected" : " is-correct";
  return chosen ? " is-wrong is-selected" : "";
}

function Number({ item }) {
  return item.la_cau_vi_du
    ? <span className="xp-no xp-no--ex">例如</span>
    : <span className="xp-no" id={`q-${item.so_cau}`}>{item.so_cau}.</span>;
}

function Mark({ mode, item }) {
  if (mode !== "review" || item.la_cau_vi_du || !item.ket_qua) return null;
  const r = item.ket_qua;
  if (r.dung === true) return <span className="xp-mark xp-mark--ok" aria-label="Đúng">✓</span>;
  if (r.dung === false) return <span className="xp-mark xp-mark--bad" aria-label={r.bo_trong ? "Bỏ trống" : "Sai"}>{r.bo_trong ? "—" : "✗"}</span>;
  return <span className="xp-mark">{r.diem != null ? `${r.diem}đ` : "Chờ chấm"}</span>;
}

function Explain({ mode, item }) {
  if (mode !== "review") return null;
  const q = item.cau_hoi;
  const transcript = q.loi_nghe;
  if (!transcript && !q.dich_nghia && !q.giai_thich && !item.ket_qua?.nhan_xet) return null;
  return (
    <details className="xp-explain">
      <summary>{transcript ? "Lời nghe, dịch nghĩa" : "Dịch nghĩa, giải thích"}</summary>
      {transcript && <p><HanziText text={transcript} pinyin={q.noi_dung ? null : q.pinyin} /></p>}
      {q.dich_nghia && <p className="xp-vi">{q.dich_nghia}</p>}
      {q.giai_thich && <p className="xp-vi">{q.giai_thich}</p>}
      {item.ket_qua?.nhan_xet && <p className="xp-vi">Nhận xét: {item.ket_qua.nhan_xet}</p>}
      {item.ket_qua?.cau_sua && <p className="zh">Câu sửa: {item.ket_qua.cau_sua}</p>}
    </details>
  );
}
// Hỏi Xiang chỉ mở khi xem lại sau khi nộp (không có trong phòng thi)
function Ask({ mode, item, luotId }) {
  if (mode !== "review" || !luotId || item.la_cau_vi_du) return null;
  return (
    <div className="xp-ask">
      <XiangChat key={item.cau_hoi.id} luotId={luotId} cauHoiId={item.cau_hoi.id} />
    </div>
  );
}
function OptionContent({ option }) {
  const { text, pinyin } = splitOption(option.noi_dung);
  return (
    <>
      {option.tep_hinh && <img src={mediaUrl(option.tep_hinh)} alt="" loading="lazy" />}
      {text && <HanziText text={text} pinyin={pinyin} />}
    </>
  );
}

function TrueFalse({ mode, item, onPick, disabled }) {
  const [yes, no] = item.cau_hoi.phuong_an;
  return (
    <div className="xp-tf" role="radiogroup" aria-label={`Câu ${item.so_cau ?? "ví dụ"}: đúng hay sai`}>
      {[[yes, "✓", "Đúng"], [no, "✗", "Sai"]].map(([opt, sign, label]) => opt && (
        <button key={opt.id} type="button" role="radio" aria-checked={item.tra_loi?.phuong_an_chon_id === opt.id}
          aria-label={label} className={`xp-tf__btn${choiceState(mode, item, opt.id)}`} disabled={disabled}
          onClick={() => onPick(item, opt.id)}>{sign}</button>
      ))}
    </div>
  );
}

function SingleRow({ mode, item, onPick, onText, disabled }) {
  const q = item.cau_hoi;
  const withImages = q.phuong_an.some((o) => o.tep_hinh);
  if (q.dang === "dung_sai") {
    return (
      <div className={`xp-row xp-row--tf${item.la_cau_vi_du ? " xp-row--ex" : ""}`}>
        <Number item={item} />
        {q.tep_hinh && <img className="xp-row__img" src={mediaUrl(q.tep_hinh)} alt={q.mo_ta_hinh || ""} loading="lazy" />}
        {q.noi_dung && <span className="xp-row__word"><HanziText text={q.noi_dung} pinyin={q.pinyin} /></span>}
        <TrueFalse mode={mode} item={item} onPick={onPick} disabled={disabled || item.la_cau_vi_du} />
        <Mark mode={mode} item={item} />
      </div>
    );
  }
  if (q.dang === "chon_mot") {
    return (
      <div className={`xp-row xp-row--mc${item.la_cau_vi_du ? " xp-row--ex" : ""}`}>
        <Number item={item} />
        <div className="xp-row__body">
          {(q.noi_dung || q.tep_hinh) && (
            <div className="xp-stem">
              {q.tep_hinh && <img src={mediaUrl(q.tep_hinh)} alt={q.mo_ta_hinh || ""} loading="lazy" />}
              {q.noi_dung && <HanziText text={q.noi_dung} pinyin={q.pinyin} />}
            </div>
          )}
          <div className={`xp-choices${withImages ? " xp-choices--img" : ""}`} role="radiogroup" aria-label={`Câu ${item.so_cau ?? "ví dụ"}`}>
            {q.phuong_an.map((opt, i) => (
              <button key={opt.id} type="button" role="radio" aria-checked={item.tra_loi?.phuong_an_chon_id === opt.id}
                className={`xp-choice${choiceState(mode, item, opt.id)}`} disabled={disabled || item.la_cau_vi_du}
                onClick={() => onPick(item, opt.id)}>
                <span className="xp-letter">{LETTERS[i]}</span>
                <OptionContent option={opt} />
              </button>
            ))}
          </div>
        </div>
        <Mark mode={mode} item={item} />
      </div>
    );
  }
  // Sắp xếp, điền chữ, viết: nhập câu trả lời
  return (
    <div className="xp-row xp-row--write">
      <Number item={item} />
      <div className="xp-row__body">
        <div className="xp-stem">
          {q.tep_hinh && <img src={mediaUrl(q.tep_hinh)} alt={q.mo_ta_hinh || ""} loading="lazy" />}
          {q.noi_dung && <HanziText text={q.noi_dung} pinyin={q.pinyin} />}
        </div>
        {q.tu_bat_buoc && <p className="xp-hint">Dùng từ: <span className="zh">{q.tu_bat_buoc}</span></p>}
        {q.dang === "sap_xep" && q.phuong_an?.length ? (
          <SentenceBuilder key={q.id} pieces={q.phuong_an} value={item.tra_loi?.van_ban || ""}
            answered={item.tra_loi?.van_ban || ""} disabled={disabled || mode === "review"} onChange={(v) => onText(item, v)} />
        ) : (
          <TextAnswer item={item} mode={mode} onText={onText} disabled={disabled} multiline={q.dang === "viet_mo"} />
        )}
        {mode === "review" && q.dap_an_chap_nhan?.length > 0 && (
          <p className="xp-answer">Đáp án: <span className="zh">{q.dap_an_chap_nhan.join(" / ")}</span></p>
        )}
      </div>
      <Mark mode={mode} item={item} />
    </div>
  );
}

function TextAnswer({ item, mode, onText, disabled, multiline }) {
  const saved = item.tra_loi?.van_ban || "";
  const [value, setValue] = useState(saved);
  useEffect(() => setValue(saved), [saved]);
  const Tag = multiline ? "textarea" : "input";
  return (
    <Tag className="xp-input zh" value={value} rows={multiline ? 4 : undefined} maxLength={2000}
      aria-label={`Câu trả lời câu ${item.so_cau}`} disabled={disabled || mode === "review"}
      onChange={(e) => setValue(e.target.value)} onBlur={() => value !== saved && onText(item, value)} />
  );
}

function GroupBlock({ mode, block, passage, onPick, disabled, luotId }) {
  const options = passage?.phuong_an ?? [];
  const withImages = options.some((o) => o.tep_hinh);
  return (
    <div className="xp-group">
      {(passage?.noi_dung || passage?.tep_hinh) && (
        <div className="xp-stem">
          {passage.tep_hinh && <img src={mediaUrl(passage.tep_hinh)} alt={passage.mo_ta_hinh || ""} loading="lazy" />}
          {passage.noi_dung && <HanziText text={passage.noi_dung} pinyin={passage.pinyin} />}
        </div>
      )}
      <div className={`xp-bank${withImages ? " xp-bank--img" : ""}`}>
        {options.map((opt, i) => (
          <div key={opt.id} className="xp-bank__item">
            <span className="xp-letter">{LETTERS[i]}</span>
            <OptionContent option={opt} />
          </div>
        ))}
      </div>
      {block.items.map((item) => (
        <div key={item.cau_hoi.id} className={`xp-row xp-row--match${item.la_cau_vi_du ? " xp-row--ex" : ""}`}>
          <Number item={item} />
          <div className="xp-row__body">
            {item.cau_hoi.noi_dung && <HanziText text={item.cau_hoi.noi_dung} pinyin={item.cau_hoi.pinyin} />}
            {!item.cau_hoi.noi_dung && !item.la_cau_vi_du && mode === "do" && <span className="xp-hint">Nghe và chọn</span>}
          </div>
          <div className="xp-letters" role="radiogroup" aria-label={`Câu ${item.so_cau ?? "ví dụ"}`}>
            {options.map((opt, i) => (
              <button key={opt.id} type="button" role="radio" aria-checked={item.tra_loi?.phuong_an_chon_id === opt.id}
                className={`xp-letter-btn${choiceState(mode, item, opt.id)}`} disabled={disabled || item.la_cau_vi_du}
                onClick={() => onPick(item, opt.id)}>{LETTERS[i]}</button>
            ))}
          </div>
          <Mark mode={mode} item={item} />
          <Explain mode={mode} item={item} />
          <Ask mode={mode} item={item} luotId={luotId} />
        </div>
      ))}
    </div>
  );
}

export default function ExamPaper({ sections, passages, mode, onPick, onText, disabled, audioUrl, luotId }) {
  return (
    <div className="xp-paper">
      {sections.map((section) => (
        <section key={section.ky_nang} className="xp-section" aria-label={section.label}>
          <h2 className="xp-section__title">{section.title} <small>{section.label}</small></h2>
          {section.ky_nang === "nghe" && audioUrl && (
            <div className="xp-audio">
              <span>Âm thanh phần Nghe</span>
              <audio controls preload="metadata" src={audioUrl} />
            </div>
          )}
          {section.parts.map((part) => (
            <div key={part.phan} className="xp-part">
              <h3 className="xp-part__title">{part.title}</h3>
              {part.from && <p className="xp-part__range">第 {part.from}{part.to !== part.from ? `–${part.to}` : ""} 题</p>}
              {part.blocks.map((block) => (block.group ? (
                <GroupBlock key={`g${block.group}`} mode={mode} block={block} passage={passages[block.group]} onPick={onPick} disabled={disabled} luotId={luotId} />
              ) : (
                <div key={block.items[0].cau_hoi.id}>
                  <SingleRow mode={mode} item={block.items[0]} onPick={onPick} onText={onText} disabled={disabled} />
                  <Explain mode={mode} item={block.items[0]} />
                  <Ask mode={mode} item={block.items[0]} luotId={luotId} />
                </div>
              )))}
            </div>
          ))}
        </section>
      ))}
    </div>
  );
}
