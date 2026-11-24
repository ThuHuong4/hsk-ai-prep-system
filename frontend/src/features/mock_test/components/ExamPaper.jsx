import { useEffect, useState } from "react";

import HanziText from "../../../shared/components/HanziText.jsx";
import SentenceBuilder from "../../../shared/components/SentenceBuilder.jsx";
import { mediaUrl } from "../../../shared/utils/format.js";
import XiangChat from "../../ai_tutor/components/XiangChat.jsx";
import ReportQuestionButton from "../../reports/components/ReportQuestionButton.jsx";
import { LETTERS, splitOption } from "../utils/paper.js";
import ProctoredAudioPlayer from "./ProctoredAudioPlayer.jsx";

// Đề thi trình bày chuẩn HSK iBT khi `mode === "do"` và chuẩn phiếu đối chiếu khi `mode === "review"`

function choiceState(mode, item, optionId) {
  const chosen = item.tra_loi?.phuong_an_chon_id === optionId;
  if (item.la_cau_vi_du) return item.cau_hoi.dap_an_id === optionId ? " is-example" : "";
  if (mode === "do") return chosen ? " is-selected" : "";
  const correct = item.cau_hoi.dap_an_id === optionId;
  if (correct) return chosen ? " is-correct is-selected" : " is-correct";
  return chosen ? " is-wrong is-selected" : "";
}

function Number({ item }) {
  return item.la_cau_vi_du ? (
    <span className="xp-no xp-no--ex">例如</span>
  ) : (
    <span className="xp-no" id={`q-${item.so_cau}`}>
      {item.so_cau}.
    </span>
  );
}

function Mark({ mode, item }) {
  if (mode !== "review" || item.la_cau_vi_du || !item.ket_qua) return null;
  const r = item.ket_qua;
  if (r.dung === true) return <span className="xp-mark xp-mark--ok" aria-label="Đúng">✓</span>;
  if (r.dung === false) {
    return (
      <span className="xp-mark xp-mark--bad" aria-label={r.bo_trong ? "Bỏ trống" : "Sai"}>
        {r.bo_trong ? "—" : "✗"}
      </span>
    );
  }
  return <span className="xp-mark">{r.diem != null ? `${r.diem}đ` : "Chờ chấm"}</span>;
}

function Explain({ mode, item }) {
  if (mode !== "review") return null;
  const q = item.cau_hoi;
  const transcript = q.loi_nghe;
  if (!transcript && !q.dich_nghia && !q.giai_thich && !item.ket_qua?.nhan_xet) return null;
  return (
    <details className="xp-explain" open={Boolean(item.ket_qua?.nhan_xet)}>
      <summary>{transcript ? "Lời nghe, dịch nghĩa & giải thích" : "Dịch nghĩa & nhận xét chấm điểm"}</summary>
      {transcript && (
        <p>
          <HanziText text={transcript} pinyin={q.noi_dung ? null : q.pinyin} />
        </p>
      )}
      {q.dich_nghia && <p className="xp-vi">{q.dich_nghia}</p>}
      {q.giai_thich && <p className="xp-vi">{q.giai_thich}</p>}
      {item.ket_qua?.nhan_xet && (
        <p className="xp-vi">
          <b>Nhận xét AI / Giảng viên:</b> {item.ket_qua.nhan_xet}
        </p>
      )}
      {item.ket_qua?.cau_sua && (
        <p className="zh">
          <b>Câu gợi ý chuẩn:</b> {item.ket_qua.cau_sua}
        </p>
      )}
      {item.ket_qua?.ly_do_sua && <p className="xp-vi">{item.ket_qua.ly_do_sua}</p>}
    </details>
  );
}

// Hỏi Xiang chỉ mở khi xem lại sau khi nộp (tắt hoàn toàn trong phòng thi)
function Ask({ mode, item, luotId }) {
  if (mode !== "review" || !luotId || item.la_cau_vi_du) return null;
  return (
    <div className="xp-ask">
      <XiangChat key={item.cau_hoi.id} luotId={luotId} cauHoiId={item.cau_hoi.id} />
      <ReportQuestionButton luotId={luotId} cauHoiId={item.cau_hoi.id} />
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

function TrueFalse({ mode, item, onPick, disabled, large = false }) {
  const [yes, no] = item.cau_hoi.phuong_an;
  return (
    <div
      className={`xp-tf${large ? " xp-tf--ibt" : ""}`}
      role="radiogroup"
      aria-label={`Câu ${item.so_cau ?? "ví dụ"}: đúng hay sai`}
    >
      {[
        [yes, "✓", "Đúng (对)", "1"],
        [no, "✗", "Sai (错)", "2"],
      ].map(
        ([opt, sign, label, keyHint]) =>
          opt && (
            <button
              key={opt.id}
              type="button"
              role="radio"
              aria-checked={item.tra_loi?.phuong_an_chon_id === opt.id}
              aria-label={label}
              className={`xp-tf__btn${choiceState(mode, item, opt.id)}`}
              disabled={disabled}
              onClick={() => onPick(item, opt.id)}
            >
              <span className="xp-tf__sign">{sign}</span>
              {large && <span className="xp-tf__label">{label}</span>}
              {large && <kbd className="xp-tf__kbd">{keyHint}</kbd>}
            </button>
          )
      )}
    </div>
  );
}

export function SingleRow({
  mode,
  item,
  onPick,
  onText,
  disabled,
  showItemAudio = false,
  luotId = null,
  maxAudioPlays = 1,
}) {
  const q = item.cau_hoi;
  const withImages = q.phuong_an.some((o) => o.tep_hinh);
  const isIbtStage = mode === "do" && !item.la_cau_vi_du;
  const itemAudio =
    showItemAudio && q.tep_audio ? (
      isIbtStage ? (
        <ProctoredAudioPlayer
          key={q.id}
          src={mediaUrl(q.tep_audio)}
          storageKey={`xianglingo-audio-${luotId || "ex"}-q-${q.id}`}
          variant="item"
          maxPlays={maxAudioPlays}
          autoPlay
        />
      ) : (
        <audio
          key={q.id}
          controls
          preload="metadata"
          src={mediaUrl(q.tep_audio)}
          style={{ width: "100%", maxWidth: 420, height: 38 }}
        />
      )
    ) : null;

  if (q.dang === "dung_sai") {
    if (isIbtStage) {
      return (
        <div className="xp-ibt-single xp-ibt-single--tf">
          {itemAudio}
          <div className="xp-ibt-stimulus">
            {q.tep_hinh && (
              <img
                className="xp-ibt-stimulus__img"
                src={mediaUrl(q.tep_hinh)}
                alt={q.mo_ta_hinh || ""}
                loading="eager"
              />
            )}
            {q.noi_dung && (
              <div className="xp-ibt-stimulus__text">
                <HanziText text={q.noi_dung} pinyin={q.pinyin} />
              </div>
            )}
          </div>
          <TrueFalse mode={mode} item={item} onPick={onPick} disabled={disabled} large />
        </div>
      );
    }
    return (
      <div className={`xp-row xp-row--tf${item.la_cau_vi_du ? " xp-row--ex" : ""}`}>
        <Number item={item} />
        <div style={{ flex: 1, display: "flex", flexDirection: "column", gap: 8 }}>
          {itemAudio}
          <div style={{ display: "flex", flexWrap: "wrap", alignItems: "center", gap: 14 }}>
            {q.tep_hinh && (
              <img className="xp-row__img" src={mediaUrl(q.tep_hinh)} alt={q.mo_ta_hinh || ""} loading="lazy" />
            )}
            {q.noi_dung && (
              <span className="xp-row__word">
                <HanziText text={q.noi_dung} pinyin={q.pinyin} />
              </span>
            )}
          </div>
        </div>
        <TrueFalse mode={mode} item={item} onPick={onPick} disabled={disabled || item.la_cau_vi_du} />
        <Mark mode={mode} item={item} />
      </div>
    );
  }

  if (q.dang === "chon_mot") {
    return (
      <div className={`xp-row xp-row--mc${item.la_cau_vi_du ? " xp-row--ex" : ""}${isIbtStage ? " xp-row--ibt" : ""}`}>
        {!isIbtStage && <Number item={item} />}
        <div className="xp-row__body">
          {itemAudio}
          {(q.noi_dung || q.tep_hinh) && (
            <div className="xp-stem">
              {q.tep_hinh && <img src={mediaUrl(q.tep_hinh)} alt={q.mo_ta_hinh || ""} loading="lazy" />}
              {q.noi_dung && <HanziText text={q.noi_dung} pinyin={q.pinyin} />}
            </div>
          )}
          <div
            className={`xp-choices${withImages ? " xp-choices--img" : " xp-choices--stack"}`}
            role="radiogroup"
            aria-label={`Câu ${item.so_cau ?? "ví dụ"}`}
          >
            {q.phuong_an.map((opt, i) => (
              <button
                key={opt.id}
                type="button"
                role="radio"
                aria-checked={item.tra_loi?.phuong_an_chon_id === opt.id}
                className={`xp-choice${choiceState(mode, item, opt.id)}`}
                disabled={disabled || item.la_cau_vi_du}
                onClick={() => onPick(item, opt.id)}
              >
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

  // Sắp xếp, điền chữ, viết mở: nhập câu trả lời bằng bộ gõ Pinyin hoặc ghép từ
  return (
    <div className={`xp-row xp-row--write${isIbtStage ? " xp-row--ibt" : ""}`}>
      {!isIbtStage && <Number item={item} />}
      <div className="xp-row__body">
        {itemAudio}
        {(q.noi_dung || q.tep_hinh) && (
          <div className="xp-stem">
            {q.tep_hinh && <img src={mediaUrl(q.tep_hinh)} alt={q.mo_ta_hinh || ""} loading="lazy" />}
            {q.noi_dung && <HanziText text={q.noi_dung} pinyin={q.pinyin} />}
          </div>
        )}
        {q.tu_bat_buoc && (
          <p className="xp-hint">
            Từ bắt buộc sử dụng: <b className="zh">{q.tu_bat_buoc}</b>
          </p>
        )}
        {q.dang === "sap_xep" && q.phuong_an?.length ? (
          <SentenceBuilder
            key={q.id}
            pieces={q.phuong_an}
            value={item.tra_loi?.van_ban || ""}
            answered={item.tra_loi?.van_ban || ""}
            disabled={disabled || mode === "review"}
            onChange={(v) => onText(item, v)}
          />
        ) : (
          <TextAnswer item={item} mode={mode} onText={onText} disabled={disabled} multiline={q.dang === "viet_mo"} />
        )}
        {mode === "review" && q.dap_an_chap_nhan?.length > 0 && (
          <p className="xp-answer">
            Đáp án chuẩn: <span className="zh">{q.dap_an_chap_nhan.join(" / ")}</span>
          </p>
        )}
      </div>
      <Mark mode={mode} item={item} />
    </div>
  );
}

function TextAnswer({ item, mode, onText, disabled, multiline }) {
  const saved = item.tra_loi?.van_ban || "";
  const [value, setValue] = useState(saved);
  const [pasteWarn, setPasteWarn] = useState(false);
  useEffect(() => setValue(saved), [saved]);

  // Tự động lưu nháp thời gian thực sau 600ms khi gõ chữ Hán để hết giờ 00:00 đột ngột vẫn không mất chữ
  useEffect(() => {
    if (mode !== "do" || disabled || value === saved) return undefined;
    const t = setTimeout(() => onText(item, value), 600);
    return () => clearTimeout(t);
  }, [value, saved, mode, disabled, item, onText]);

  function blockPasteOrDrop(e) {
    if (mode !== "do") return;
    e.preventDefault();
    setPasteWarn(true);
    setTimeout(() => setPasteWarn(false), 4000);
  }

  const Tag = multiline ? "textarea" : "input";
  return (
    <div className="xp-write-wrap">
      <Tag
        className="xp-input zh"
        value={value}
        rows={multiline ? 6 : undefined}
        maxLength={2000}
        placeholder={multiline ? "Nhập đoạn văn chữ Hán bằng bộ gõ Pinyin…" : "Nhập đáp án chữ Hán…"}
        aria-label={`Câu trả lời câu ${item.so_cau}`}
        disabled={disabled || mode === "review"}
        onChange={(e) => setValue(e.target.value)}
        onPaste={blockPasteOrDrop}
        onDrop={blockPasteOrDrop}
        onBlur={() => value !== saved && onText(item, value)}
      />
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: 8 }}>
        {pasteWarn ? (
          <span role="alert" style={{ fontSize: "12.5px", fontWeight: 700, color: "var(--bad)" }}>
            ⚠ Quy chế thi HSK: Đã chặn thao tác Dán (Paste) — vui lòng tự gõ chữ Hán bằng bộ gõ Pinyin.
          </span>
        ) : (
          <span />
        )}
        {multiline && mode === "do" && (
          <span className="xp-char-count">{[...value.replace(/\s+/g, "")].length} chữ Hán / ký tự</span>
        )}
      </div>
    </div>
  );
}

export function GroupBlock({
  mode,
  block,
  passage,
  onPick,
  disabled,
  luotId,
  showItemAudio = false,
  maxAudioPlays = 1,
  activeQuestionNo = null,
  onFocusQuestion = null,
}) {
  const options = passage?.phuong_an ?? [];
  const withImages = options.some((o) => o.tep_hinh);
  const isExampleOnly = block.items.every((x) => x.la_cau_vi_du);
  const hasStimulus = Boolean(
    (showItemAudio && passage?.tep_audio) || passage?.noi_dung || passage?.tep_hinh || options.length > 0
  );
  const useSplitPane = mode === "do" && !isExampleOnly && hasStimulus;

  const stimulusNode = hasStimulus ? (
    <div className="xp-group__stimulus">
      {showItemAudio &&
        passage?.tep_audio &&
        (mode === "do" ? (
          <ProctoredAudioPlayer
            key={passage.id}
            src={mediaUrl(passage.tep_audio)}
            storageKey={`xianglingo-audio-${luotId || "ex"}-p-${passage.id}`}
            variant="item"
            maxPlays={maxAudioPlays}
            autoPlay
          />
        ) : (
          <audio
            key={passage.id}
            controls
            preload="metadata"
            src={mediaUrl(passage.tep_audio)}
            style={{ width: "100%", maxWidth: 440, height: 38 }}
          />
        ))}
      {(passage?.noi_dung || passage?.tep_hinh) && (
        <div className="xp-stem xp-stem--passage">
          {passage.tep_hinh && <img src={mediaUrl(passage.tep_hinh)} alt={passage.mo_ta_hinh || ""} loading="lazy" />}
          {passage.noi_dung && <HanziText text={passage.noi_dung} pinyin={passage.pinyin} />}
        </div>
      )}
      {options.length > 0 && (
        <div className={`xp-bank${withImages ? " xp-bank--img" : ""}`}>
          {options.map((opt, i) => (
            <div key={opt.id} className="xp-bank__item">
              <span className="xp-letter">{LETTERS[i]}</span>
              <OptionContent option={opt} />
            </div>
          ))}
        </div>
      )}
    </div>
  ) : null;

  const questionsNode = (
    <div className="xp-group__questions">
      {block.items.map((item) => {
        const subOpts = options.length > 0 ? options : item.cau_hoi.phuong_an ?? [];
        const isCurrentSub = mode === "do" && !item.la_cau_vi_du && activeQuestionNo === item.so_cau;
        return (
          <div
            key={item.cau_hoi.id}
            className={`xp-row xp-row--match${item.la_cau_vi_du ? " xp-row--ex" : ""}${isCurrentSub ? " is-active-sub" : ""}`}
            onClick={() => {
              if (mode === "do" && !item.la_cau_vi_du && onFocusQuestion) {
                onFocusQuestion(item.so_cau);
              }
            }}
          >
            <Number item={item} />
            <div className="xp-row__body">
              {showItemAudio &&
                item.cau_hoi.tep_audio &&
                (mode === "do" && !item.la_cau_vi_du ? (
                  <ProctoredAudioPlayer
                    key={item.cau_hoi.id}
                    src={mediaUrl(item.cau_hoi.tep_audio)}
                    storageKey={`xianglingo-audio-${luotId || "ex"}-q-${item.cau_hoi.id}`}
                    variant="item"
                    maxPlays={maxAudioPlays}
                  />
                ) : (
                  <audio
                    key={item.cau_hoi.id}
                    controls
                    preload="metadata"
                    src={mediaUrl(item.cau_hoi.tep_audio)}
                    style={{ width: "100%", maxWidth: 380, height: 36 }}
                  />
                ))}
              {item.cau_hoi.noi_dung && <HanziText text={item.cau_hoi.noi_dung} pinyin={item.cau_hoi.pinyin} />}
              {!item.cau_hoi.noi_dung && !item.la_cau_vi_du && mode === "do" && (
                <span className="xp-hint">Nghe âm thanh và chọn phương án phù hợp</span>
              )}

              {/* Nếu câu con có bộ phương án đầy đủ riêng (Đọc hiểu đoạn văn nhiều câu hỏi A/B/C/D) */}
              {options.length === 0 && subOpts.length > 0 && (
                <div className="xp-choices xp-choices--stack" role="radiogroup" aria-label={`Câu ${item.so_cau ?? "ví dụ"}`}>
                  {subOpts.map((opt, i) => (
                    <button
                      key={opt.id}
                      type="button"
                      role="radio"
                      aria-checked={item.tra_loi?.phuong_an_chon_id === opt.id}
                      className={`xp-choice${choiceState(mode, item, opt.id)}`}
                      disabled={disabled || item.la_cau_vi_du}
                      onClick={(e) => {
                        e.stopPropagation();
                        onPick(item, opt.id);
                      }}
                    >
                      <span className="xp-letter">{LETTERS[i]}</span>
                      <OptionContent option={opt} />
                    </button>
                  ))}
                </div>
              )}
            </div>

            {options.length > 0 && (
              <div className="xp-letters" role="radiogroup" aria-label={`Câu ${item.so_cau ?? "ví dụ"}`}>
                {options.map((opt, i) => (
                  <button
                    key={opt.id}
                    type="button"
                    role="radio"
                    aria-checked={item.tra_loi?.phuong_an_chon_id === opt.id}
                    className={`xp-letter-btn${choiceState(mode, item, opt.id)}`}
                    disabled={disabled || item.la_cau_vi_du}
                    onClick={(e) => {
                      e.stopPropagation();
                      onPick(item, opt.id);
                    }}
                  >
                    {LETTERS[i]}
                  </button>
                ))}
              </div>
            )}
            <Mark mode={mode} item={item} />
            <Explain mode={mode} item={item} />
            <Ask mode={mode} item={item} luotId={luotId} />
          </div>
        );
      })}
    </div>
  );

  return (
    <div className={`xp-group${useSplitPane ? " xp-group--split" : ""}`}>
      {stimulusNode}
      {questionsNode}
    </div>
  );
}

export default function ExamPaper({ sections, passages, mode, onPick, onText, disabled, audioUrl, luotId }) {
  return (
    <div className="xp-paper">
      {sections.map((section) => (
        <section key={section.ky_nang} className="xp-section" aria-label={section.label}>
          <h2 className="xp-section__title">
            {section.title} <small>{section.label}</small>
          </h2>
          {section.ky_nang === "nghe" && audioUrl && (
            <div className="xp-audio">
              <span>Âm thanh phần Nghe</span>
              <audio controls preload="metadata" src={audioUrl} />
            </div>
          )}
          {section.parts.map((part) => (
            <div key={part.phan} className="xp-part">
              <h3 className="xp-part__title">{part.title}</h3>
              {part.from && (
                <p className="xp-part__range">
                  第 {part.from}
                  {part.to !== part.from ? `–${part.to}` : ""} 题
                </p>
              )}
              {part.blocks.map((block) =>
                block.group ? (
                  <GroupBlock
                    key={`g${block.group}`}
                    mode={mode}
                    block={block}
                    passage={passages[block.group]}
                    onPick={onPick}
                    disabled={disabled}
                    luotId={luotId}
                    showItemAudio={section.ky_nang === "nghe" && !audioUrl}
                  />
                ) : (
                  <div key={block.items[0].cau_hoi.id}>
                    <SingleRow
                      mode={mode}
                      item={block.items[0]}
                      onPick={onPick}
                      onText={onText}
                      disabled={disabled}
                      luotId={luotId}
                      showItemAudio={section.ky_nang === "nghe" && !audioUrl}
                    />
                    <Explain mode={mode} item={block.items[0]} />
                    <Ask mode={mode} item={block.items[0]} luotId={luotId} />
                  </div>
                )
              )}
            </div>
          ))}
        </section>
      ))}
    </div>
  );
}
