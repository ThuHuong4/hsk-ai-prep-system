import { useRef, useState } from "react";

import { useAuth } from "../../auth/context/AuthContext.jsx";
import Icon from "../../../shared/components/Icon.jsx";
import { uploadMedia } from "../api/lecturerApi.js";
import { mediaUrl } from "../utils/labels.js";

const ACCEPT = { audio: ".mp3,.m4a,.wav,.ogg", hinh: ".png,.jpg,.jpeg,.webp,.gif" };

// Chọn tệp tải lên HOẶC bấm nút tạo bằng AI miễn phí → lưu đường dẫn tương đối vào value
export default function MediaInput({ kind, label, value, onChange, disabled, onAiGenerate, aiLabel }) {
  const { token } = useAuth();
  const [uploading, setUploading] = useState(false);
  const [aiBusy, setAiBusy] = useState(false);
  const [error, setError] = useState("");
  const inputRef = useRef(null);
  const busy = uploading || aiBusy;

  async function handleFile(event) {
    const file = event.target.files?.[0];
    event.target.value = "";
    if (!file) return;
    setUploading(true);
    setError("");
    try {
      const data = await uploadMedia(token, kind, file);
      onChange(data.duong_dan);
    } catch (err) {
      setError(err?.message || "Tải tệp thất bại");
    } finally {
      setUploading(false);
    }
  }

  async function handleAi() {
    if (!onAiGenerate || busy || disabled) return;
    setAiBusy(true);
    setError("");
    try {
      const path = await onAiGenerate();
      if (path) onChange(path);
    } catch (err) {
      setError(err?.message || "AI chưa tạo được tệp, vui lòng thử lại");
    } finally {
      setAiBusy(false);
    }
  }

  const url = mediaUrl(value);
  const resolvedAiLabel = aiLabel || (kind === "audio" ? "Tạo giọng đọc AI" : "Tạo hình AI");

  return (
    <div className="lv-media">
      {label && <span className="lv-media__label">{label}</span>}
      {url && kind === "hinh" && <img className="lv-media__img" src={url} alt="" />}
      {url && kind === "audio" && <audio controls preload="none" src={url} />}
      <div className="lv-media__actions">
        {onAiGenerate && (
          <button type="button" className="xbtn xbtn--ghost xbtn--sm" onClick={handleAi} disabled={disabled || busy}>
            <Icon name="spark" size={14} /> {aiBusy ? "AI đang tạo…" : value ? `${resolvedAiLabel} lại` : resolvedAiLabel}
          </button>
        )}
        <button type="button" className="xbtn xbtn--ghost xbtn--sm" onClick={() => inputRef.current?.click()} disabled={disabled || busy}>
          {uploading ? "Đang tải…" : value ? "Đổi tệp" : "Chọn tệp"}
        </button>
        {value && (
          <button type="button" className="xlink xlink--danger" onClick={() => onChange(null)} disabled={disabled || busy}>
            Bỏ tệp
          </button>
        )}
      </div>
      <input ref={inputRef} type="file" accept={ACCEPT[kind]} hidden onChange={handleFile} />
      {error && <span className="ae-err" role="alert">{error}</span>}
    </div>
  );
}
