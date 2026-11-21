import { useRef, useState } from "react";

import { useAuth } from "../../auth/context/AuthContext.jsx";
import { uploadMedia } from "../api/lecturerApi.js";
import { mediaUrl } from "../utils/labels.js";

const ACCEPT = { audio: ".mp3,.m4a,.wav,.ogg", hinh: ".png,.jpg,.jpeg,.webp,.gif" };

// Chọn tệp → tải lên ngay → lưu đường dẫn tương đối vào value
export default function MediaInput({ kind, label, value, onChange, disabled }) {
  const { token } = useAuth();
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState("");
  const inputRef = useRef(null);

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

  const url = mediaUrl(value);
  return (
    <div className="lv-media">
      <span className="lv-media__label">{label}</span>
      {url && kind === "hinh" && <img className="lv-media__img" src={url} alt="" />}
      {url && kind === "audio" && <audio controls preload="none" src={url} />}
      <div className="lv-media__actions">
        <button type="button" className="xbtn xbtn--ghost xbtn--sm" onClick={() => inputRef.current?.click()} disabled={disabled || uploading}>
          {uploading ? "Đang tải…" : value ? "Đổi tệp" : "Chọn tệp"}
        </button>
        {value && (
          <button type="button" className="xlink xlink--danger" onClick={() => onChange(null)} disabled={disabled || uploading}>
            Bỏ tệp
          </button>
        )}
      </div>
      <input ref={inputRef} type="file" accept={ACCEPT[kind]} hidden onChange={handleFile} />
      {error && <span role="alert">{error}</span>}
    </div>
  );
}
