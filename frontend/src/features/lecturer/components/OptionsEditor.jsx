import { useAuth } from "../../auth/context/AuthContext.jsx";
import { aiMakeImage } from "../api/lecturerApi.js";
import MediaInput from "./MediaInput.jsx";
import { newKey } from "../utils/questionForm.js";
import { optionLetter } from "../utils/labels.js";

// mode: "correct" (chọn 1 đáp án đúng) | "plain" (không có đáp án đúng: bộ chung, mảnh sắp xếp) | "fixed" (Đúng/Sai)
export default function OptionsEditor({ options, onChange, mode, title, allowImage = true, disabled, name }) {
  const { token } = useAuth();
  function update(index, patch) {
    onChange(options.map((o, i) => (i === index ? { ...o, ...patch } : o)));
  }
  async function generateOptionImage(index) {
    const current = options[index];
    const entered = window.prompt(
      `Nhập mô tả hình cho phương án ${optionLetter(index)} (bằng tiếng Việt):`,
      (current?.noi_dung || "").trim(),
    );
    if (entered === null) return null;
    const desc = entered.trim();
    if (desc.length < 2) throw new Error("Cần nhập mô tả bức tranh");
    const data = await aiMakeImage(token, desc);
    return data.duong_dan;
  }
  function markCorrect(index) {
    onChange(options.map((o, i) => ({ ...o, la_dap_an_dung: i === index })));
  }
  function remove(index) {
    onChange(options.filter((_, i) => i !== index));
  }
  function add() {
    onChange([...options, { key: newKey(), noi_dung: "", tep_hinh: null, la_dap_an_dung: false }]);
  }

  return (
    <fieldset className="lv-options" disabled={disabled}>
      <legend>{title}</legend>
      {options.map((o, i) => (
        <div className="lv-option" key={o.key}>
          <span className="lv-option__letter">{optionLetter(i)}</span>
          {mode !== "plain" && (
            <label className="lv-option__correct">
              <input type="radio" name={name} checked={Boolean(o.la_dap_an_dung)} onChange={() => markCorrect(i)} />
              Đúng
            </label>
          )}
          {mode === "fixed" ? (
            <span className="lv-option__fixed">{o.noi_dung}</span>
          ) : (
            <input
              className="zh"
              value={o.noi_dung}
              placeholder={allowImage ? "Nội dung (hoặc chọn hình)" : "Nội dung"}
              maxLength={1000}
              onChange={(e) => update(i, { noi_dung: e.target.value })}
            />
          )}
          {allowImage && mode !== "fixed" && (
            <MediaInput kind="hinh" label="" value={o.tep_hinh} onChange={(v) => update(i, { tep_hinh: v })}
              onAiGenerate={() => generateOptionImage(i)} aiLabel="Tạo hình" disabled={disabled} />
          )}
          {mode !== "fixed" && options.length > 2 && (
            <button type="button" className="xlink xlink--danger" onClick={() => remove(i)} aria-label={`Xóa phương án ${optionLetter(i)}`}>
              Xóa
            </button>
          )}
        </div>
      ))}
      {mode !== "fixed" && options.length < 12 && (
        <button type="button" className="xbtn xbtn--ghost xbtn--sm" onClick={add}>+ Thêm phương án</button>
      )}
    </fieldset>
  );
}
