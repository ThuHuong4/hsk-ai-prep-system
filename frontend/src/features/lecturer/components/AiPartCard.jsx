import { Link } from "react-router-dom";

import Icon from "../../../shared/components/Icon.jsx";
import { mediaUrl } from "../../../shared/utils/format.js";
import { canCheck, LETTERS, mediaSlots, missingMedia, slotId } from "../utils/aiExamParts.js";

/** Một mục AI soạn trong trang Soạn đề với AI: xem hình, nghe âm thanh, đáp án, lỗi AI soát, trùng ngân hàng. */

function UploadButton({ accept, onFile, disabled }) {
  return (
    <label className={`xbtn xbtn--ghost xbtn--sm ae-upload${disabled ? " is-disabled" : ""}`}>
      <Icon name="upload" size={14} /> Tải tệp của tôi
      <input type="file" accept={accept} disabled={disabled} hidden
        onChange={(e) => { const f = e.target.files?.[0]; e.target.value = ""; if (f) onFile(f); }} />
    </label>
  );
}

function MediaImage({ src, desc, id, media, onRegen, onUpload, locked, alt }) {
  const state = media[id];
  return (
    <figure className="ae-img">
      {src ? <img src={mediaUrl(src)} alt={alt || desc || ""} loading="lazy" /> : (
        <div className="ae-img__empty">{state === "dang" ? "Đang tạo hình…" : "Chưa có hình"}</div>
      )}
      {desc && <figcaption>{desc}</figcaption>}
      {typeof state === "string" && state !== "dang" && <span className="ae-err">{state}</span>}
      {!locked && (
        <button type="button" className="xbtn xbtn--ghost xbtn--sm" onClick={onRegen} disabled={state === "dang"}>
          <Icon name="replay" size={14} /> {src ? "Tạo lại hình" : "Tạo hình"}
        </button>
      )}
      {!locked && <UploadButton accept="image/png,image/jpeg,image/webp" onFile={onUpload} disabled={state === "dang"} />}
    </figure>
  );
}

function MediaAudio({ src, id, media, onRegen, onUpload, locked, continuousTape }) {
  const state = media[id];
  if (continuousTape && src && state !== "dang") {
    return (
      <div className="ae-audio ae-audio--in-tape">
        <span className="ae-tape-badge">🎧 Phát liền mạch trong băng Nghe chung toàn đề</span>
        {!locked && (
          <details className="ae-audio-override">
            <summary>Đổi giọng đọc / tệp riêng câu này</summary>
            <div className="ae-audio">
              <audio controls preload="none" src={mediaUrl(src)} />
              <button type="button" className="xbtn xbtn--ghost xbtn--sm" onClick={onRegen}>
                <Icon name="replay" size={14} /> Tạo lại giọng đọc
              </button>
              <UploadButton accept=".mp3,.m4a,.wav,.ogg,audio/*" onFile={onUpload} />
            </div>
          </details>
        )}
      </div>
    );
  }
  return (
    <div className="ae-audio">
      {src ? <audio controls preload="none" src={mediaUrl(src)} /> : (
        <span className="ae-img__empty ae-img__empty--line">{state === "dang" ? "Đang tạo giọng đọc…" : "Chưa có âm thanh"}</span>
      )}
      {!locked && (
        <button type="button" className="xbtn xbtn--ghost xbtn--sm" onClick={onRegen} disabled={state === "dang"}>
          <Icon name="replay" size={14} /> {src ? "Tạo lại âm thanh" : "Tạo âm thanh"}
        </button>
      )}
      {!locked && <UploadButton accept=".mp3,.m4a,.wav,.ogg,audio/*" onFile={onUpload} disabled={state === "dang"} />}
      {typeof state === "string" && state !== "dang" && <span className="ae-err">{state}</span>}
    </div>
  );
}

function Options({ options, answer, base, media, onRegen, onUpload, locked }) {
  if (!options?.length) return null;
  const images = options.some((o) => "tep_hinh" in o);
  return (
    <ol className={images ? "ae-opts ae-opts--img" : "ae-opts"}>
      {options.map((o, i) => (
        <li key={i} className={answer === i + 1 ? "is-right" : ""}>
          <b>{LETTERS[i]}</b>
          {images ? (
            <MediaImage src={o.tep_hinh} desc={o.mo_ta_hinh} id={slotId([...base, i, "tep_hinh"])} media={media}
              locked={locked} onRegen={() => onRegen([...base, i, "tep_hinh"])}
              onUpload={(f) => onUpload([...base, i, "tep_hinh"], f)} />
          ) : <span className="zh">{o.noi_dung}</span>}
        </li>
      ))}
    </ol>
  );
}

function Transcript({ text, pinyin }) {
  if (!text) return null;
  return (
    <div className="ae-script">
      <p className="lv-ai__label">Lời nghe</p>
      <p className="zh">{text}</p>
      {pinyin && <p className="ae-pinyin">{pinyin}</p>}
    </div>
  );
}

export default function AiPartCard({ card, from, label, media, onRegen, onUpload, onRedo, onRemove, onToggle, busy, review }) {
  const m = card.muc;
  const locked = Boolean(card.duyet) || Boolean(review?.locked);
  const lack = missingMedia(m);
  const to = from + card.so_cau - 1;
  const pending = mediaSlots(m).some((s) => media[slotId(s.path)] === "dang");
  return (
    <li className={`ae-card${locked ? " ae-card--done" : ""}`}>
      <div className="ae-card__head">
        <b>{from === to ? `Câu ${from}` : `Câu ${from}–${to}`}</b>
        <span className="ae-tag">{label}</span>
        {locked && (
          <Link className="ae-ok" to={`/giang-vien/cau-hoi/${card.duyet.id}`}>
            <Icon name="check" size={14} /> Đã duyệt · #{card.duyet.id}
          </Link>
        )}
      </div>

      {"tep_hinh" in m && (
        <MediaImage src={m.tep_hinh} desc={m.mo_ta_hinh} id="tep_hinh" media={media} locked={locked}
          onRegen={() => onRegen(["tep_hinh"])} onUpload={(f) => onUpload(["tep_hinh"], f)} />
      )}
      {"tep_audio" in m && (
        <MediaAudio src={m.tep_audio} id="tep_audio" media={media} locked={locked}
          continuousTape={Boolean(review?.continuousTape)}
          onRegen={() => onRegen(["tep_audio"])}
          onUpload={(f) => onUpload(["tep_audio"], f)} />
      )}
      <Transcript text={m.loi_nghe} pinyin={m.pinyin_nghe} />
      {m.noi_dung && (
        <div>
          <p className="zh ae-text">{m.noi_dung}</p>
          {m.pinyin && <p className="ae-pinyin">{m.pinyin}</p>}
        </div>
      )}
      {m.tu_bat_buoc && <p>Từ cho sẵn: <b className="zh">{m.tu_bat_buoc}</b></p>}

      <Options options={m.lua_chon} answer={typeof m.dap_an === "number" ? m.dap_an : null} base={["lua_chon"]}
        media={media} onRegen={onRegen} onUpload={onUpload} locked={locked} />

      {typeof m.dap_an === "boolean" && <p className="ae-key">Đáp án: <b>{m.dap_an ? "Đúng (✓)" : "Sai (✗)"}</b></p>}
      {m.thu_tu_dung && <p className="ae-key">Thứ tự đúng: <b>{m.thu_tu_dung.map((n) => LETTERS[n - 1]).join(" ")}</b></p>}
      {m.dap_an_chap_nhan?.length > 0 && (
        <p className="ae-key">Đáp án chấp nhận: <b className="zh">{m.dap_an_chap_nhan.join(" | ")}</b></p>
      )}
      {m.tieu_chi && <p className="ae-key">Tiêu chí chấm: {m.tieu_chi}</p>}
      {m.cau_mau && <p className="ae-key">Câu mẫu: <span className="zh">{m.cau_mau}</span></p>}

      {m.cau?.length > 0 && (
        <ol className="ae-children" start={from}>
          {m.cau.map((c, i) => (
            <li key={i} id={`cau-${from + i}`} style={{ scrollMarginTop: 96 }}>
              {"tep_audio" in c && (
                <MediaAudio src={c.tep_audio} id={slotId(["cau", i, "tep_audio"])} media={media} locked={locked}
                  continuousTape={Boolean(review?.continuousTape)}
                  onRegen={() => onRegen(["cau", i, "tep_audio"])} onUpload={(f) => onUpload(["cau", i, "tep_audio"], f)} />
              )}
              {c.loi_nghe && <p className="zh ae-pre">{c.loi_nghe}</p>}
              {c.noi_dung && <p className="zh">{c.noi_dung}</p>}
              {c.pinyin && <p className="ae-pinyin">{c.pinyin}</p>}
              {c.lua_chon ? (
                <Options options={c.lua_chon} answer={c.dap_an} base={["cau", i, "lua_chon"]} media={media}
                  onRegen={onRegen} onUpload={onUpload} locked={locked} />
              ) : (
                <p className="ae-key">Đáp án: <b>{c.dap_an ? LETTERS[c.dap_an - 1] : "chưa có"}</b></p>
              )}
              {c.giai_thich && <p className="ae-note">{c.giai_thich}</p>}
            </li>
          ))}
        </ol>
      )}

      {(m.dich_nghia || m.giai_thich) && (
        <details className="ae-more">
          <summary>Nghĩa và giải thích</summary>
          {m.dich_nghia && <p>{m.dich_nghia}</p>}
          {m.giai_thich && <p>{m.giai_thich}</p>}
        </details>
      )}

      {review ? (
        <>
          {review.red.length > 0 && <div className="lv-alert ae-flags"><b>Cần xử lý:</b><ul>{review.red.map((v, i) => <li key={i}>{v}</li>)}</ul></div>}
          {review.yellow.length > 0 && <div className="lv-ai__warn ae-flags"><b>Cần nhìn kỹ:</b><ul>{review.yellow.map((v, i) => <li key={i}>{v}</li>)}</ul></div>}
          {review.red.length === 0 && review.yellow.length === 0 && <p className="lv-ai__ok">Đã qua mọi lớp kiểm tra tự động.</p>}
          {card.trung_lap?.length > 0 && (
            <p className="ae-note">Câu gần trùng:{" "}
              {card.trung_lap.map((d) => <Link key={d.id} to={`/giang-vien/cau-hoi/${d.id}`} target="_blank">#{d.id} </Link>)}
            </p>
          )}
          {review.actions}
        </>
      ) : (
        <>
        {card.loi && <p className="lv-alert">Thiếu thành phần: {card.loi}</p>}
        {card.loi_duyet && <p className="lv-alert">{card.loi_duyet}</p>}
        {card.van_de_ai === null && <p className="lv-ai__warn">AI chưa soát được mục này, bạn tự kiểm tra kỹ.</p>}
        {card.van_de_ai?.length > 0 && (
          <div className="lv-ai__warn"><b>AI soát thấy:</b><ul>{card.van_de_ai.map((v, i) => <li key={i}>{v}</li>)}</ul></div>
        )}
        {Array.isArray(card.van_de_ai) && card.van_de_ai.length === 0 && !card.loi && (
          <p className="lv-ai__ok">AI soát: không thấy lỗi nội dung.</p>
        )}
        {card.trung_lap?.length > 0 && (
          <div className="lv-ai__warn">
            <b>Gần trùng câu đã có trong ngân hàng:</b>
            <ul>
              {card.trung_lap.map((d) => (
                <li key={d.id}>
                  <Link to={`/giang-vien/cau-hoi/${d.id}`} target="_blank">#{d.id}</Link> ({Math.round(d.do_giong * 100)}%):{" "}
                  <span className="zh">{d.noi_dung}</span>
                </li>
              ))}
            </ul>
          </div>
        )}
        {!locked && card.luu_y?.length > 0 && <ul className="ae-tips">{card.luu_y.map((t, i) => <li key={i}>{t}</li>)}</ul>}

        {!locked && (
          <div className="ae-card__actions">
            <label className="ae-check">
              <input type="checkbox" checked={Boolean(card.da_kiem_tra)} disabled={!canCheck(card) || pending}
                onChange={onToggle} />
              Tôi đã xem hình, nghe âm thanh và kiểm tra nội dung
              {lack.length > 0 && <small> (còn thiếu: {lack.map((s) => s.ten).join(", ")})</small>}
            </label>
            <button type="button" className="xbtn xbtn--ghost xbtn--sm" onClick={onRedo} disabled={busy}>
              <Icon name="spark" size={14} /> Soạn lại mục này
            </button>
            <button type="button" className="xbtn xbtn--ghost xbtn--sm" onClick={onRemove} disabled={busy}>
              <Icon name="x" size={14} /> Bỏ
            </button>
          </div>
        )}
        </>
      )}
    </li>
  );
}
