import { useState } from "react";

import MediaInput from "./MediaInput.jsx";
import OptionsEditor from "./OptionsEditor.jsx";
import { optionLetter } from "../utils/labels.js";

// Phần nội dung + đáp án dùng chung cho câu đơn và câu con
export default function QuestionFields({ q, onChange, idPrefix, sharedCount = 0, disabled }) {
  const [showMore, setShowMore] = useState(Boolean(q.pinyin || q.dich_nghia || q.goi_y || q.loi_nghe || q.mo_ta_hinh));
  const set = (patch) => onChange({ ...q, ...patch });
  const field = (name, label, props = {}) => (
    <div className="lv-field">
      <label htmlFor={`${idPrefix}-${name}`}>{label}</label>
      <textarea
        id={`${idPrefix}-${name}`}
        rows={props.rows ?? 2}
        className={props.zh ? "zh" : undefined}
        value={q[name] ?? ""}
        maxLength={props.max ?? 5000}
        onChange={(e) => set({ [name]: e.target.value })}
        disabled={disabled}
      />
    </div>
  );

  return (
    <div className="lv-qfields">
      {field("noi_dung", q.dang === "chon_bo_chung" ? "Nội dung câu (có thể để trống nếu chỉ nghe)" : "Nội dung / đề bài", { rows: 3, zh: true })}

      <div className="lv-media-row">
        <MediaInput kind="hinh" label="Hình" value={q.tep_hinh} onChange={(v) => set({ tep_hinh: v })} disabled={disabled} />
        <MediaInput kind="audio" label="Âm thanh" value={q.tep_audio} onChange={(v) => set({ tep_audio: v })} disabled={disabled} />
      </div>

      {/* Phần đáp án theo dạng */}
      {q.dang === "chon_mot" && (
        <OptionsEditor name={`${idPrefix}-correct`} title="Phương án (chọn 1 đáp án đúng)" mode="correct"
          options={q.phuong_an} onChange={(v) => set({ phuong_an: v })} disabled={disabled} />
      )}
      {q.dang === "dung_sai" && (
        <OptionsEditor name={`${idPrefix}-correct`} title="Đáp án" mode="fixed" allowImage={false}
          options={q.phuong_an} onChange={(v) => set({ phuong_an: v })} disabled={disabled} />
      )}
      {q.dang === "chon_bo_chung" && (
        <div className="lv-field">
          <label htmlFor={`${idPrefix}-dapan`}>Đáp án trong bộ phương án chung</label>
          <select id={`${idPrefix}-dapan`} value={q.dap_an_thu_tu ?? ""} disabled={disabled}
            onChange={(e) => set({ dap_an_thu_tu: e.target.value ? Number(e.target.value) : null })}>
            <option value="">— Chọn —</option>
            {Array.from({ length: sharedCount }, (_, i) => (
              <option key={i} value={i + 1}>{optionLetter(i)}</option>
            ))}
          </select>
          {sharedCount < 2 && <small className="lv-help">Thêm ít nhất 2 phương án chung ở phần ngữ liệu phía trên.</small>}
        </div>
      )}
      {q.dang === "sap_xep" && (
        <OptionsEditor name={`${idPrefix}-frag`} title="Các mảnh để sắp xếp (theo thứ tự hiển thị)" mode="plain" allowImage={false}
          options={q.phuong_an} onChange={(v) => set({ phuong_an: v })} disabled={disabled} />
      )}
      {(q.dang === "sap_xep" || q.dang === "dien_chu") && (
        <AcceptedAnswers idPrefix={idPrefix} values={q.dap_an_chap_nhan} disabled={disabled}
          label={q.dang === "sap_xep" ? "Câu đúng sau khi sắp xếp" : "Đáp án chấp nhận"}
          onChange={(v) => set({ dap_an_chap_nhan: v })} />
      )}
      {q.dang === "viet_mo" && (
        <div className="lv-grid-3">
          <div className="lv-field">
            <label htmlFor={`${idPrefix}-max`}>Điểm tối đa</label>
            <input id={`${idPrefix}-max`} type="number" min="0.5" step="0.5" value={q.diem_toi_da} disabled={disabled}
              onChange={(e) => set({ diem_toi_da: e.target.value })} />
          </div>
          <div className="lv-field">
            <label htmlFor={`${idPrefix}-pass`}>Ngưỡng đạt</label>
            <input id={`${idPrefix}-pass`} type="number" min="0.5" step="0.5" value={q.nguong_dat} disabled={disabled}
              onChange={(e) => set({ nguong_dat: e.target.value })} />
          </div>
          <div className="lv-field">
            <label htmlFor={`${idPrefix}-word`}>Từ bắt buộc (nếu có)</label>
            <input id={`${idPrefix}-word`} className="zh" maxLength={20} value={q.tu_bat_buoc} disabled={disabled}
              onChange={(e) => set({ tu_bat_buoc: e.target.value })} />
          </div>
        </div>
      )}
      {q.dang === "viet_mo" && field("tieu_chi_mo_ta", "Tiêu chí chấm (AI dựa vào đây)", { rows: 3 })}

      {field("giai_thich", "Giải thích đáp án")}

      <button type="button" className="xlink" onClick={() => setShowMore((v) => !v)} aria-expanded={showMore}>
        {showMore ? "Ẩn thông tin thêm" : "Thêm pinyin, dịch nghĩa, lời nghe, gợi ý…"}
      </button>
      {showMore && (
        <div className="lv-more">
          {field("pinyin", "Pinyin")}
          {field("dich_nghia", "Dịch nghĩa")}
          {field("loi_nghe", "Lời nghe (transcript)", { zh: true })}
          {field("mo_ta_hinh", "Mô tả hình (cho người dùng trình đọc màn hình)", { max: 1000 })}
          {field("goi_y", "Gợi ý", { max: 2000 })}
        </div>
      )}
    </div>
  );
}

function AcceptedAnswers({ idPrefix, values, onChange, label, disabled }) {
  const list = values.length ? values : [""];
  return (
    <fieldset className="lv-options" disabled={disabled}>
      <legend>{label}</legend>
      {list.map((value, i) => (
        <div className="lv-option" key={i}>
          <input
            id={`${idPrefix}-acc-${i}`}
            className="zh"
            value={value}
            maxLength={1000}
            aria-label={`${label} ${i + 1}`}
            onChange={(e) => onChange(list.map((v, j) => (j === i ? e.target.value : v)))}
          />
          {list.length > 1 && (
            <button type="button" className="xlink xlink--danger" onClick={() => onChange(list.filter((_, j) => j !== i))}>Xóa</button>
          )}
        </div>
      ))}
      {list.length < 10 && <button type="button" className="xbtn xbtn--ghost xbtn--sm" onClick={() => onChange([...list, ""])}>+ Thêm đáp án chấp nhận</button>}
    </fieldset>
  );
}
