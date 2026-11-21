import { useEffect, useState } from "react";

import { useAuth } from "../../auth/context/AuthContext.jsx";
import { fetchMaterialBlobUrl } from "../api/lecturerApi.js";

// "Xem như học viên": tải tệp có kiểm tra quyền rồi hiển thị trong khung (ảnh/PDF) hoặc trình phát (audio)
export default function MaterialViewer({ id, type, title }) {
  const { token } = useAuth();
  const [url, setUrl] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => {
    let created = null;
    let cancelled = false;
    setUrl(null);
    setError("");
    fetchMaterialBlobUrl(token, id)
      .then((u) => { created = u; if (!cancelled) setUrl(u); else URL.revokeObjectURL(u); })
      .catch((err) => !cancelled && setError(err?.message || "Không mở được tệp"));
    return () => { cancelled = true; if (created) URL.revokeObjectURL(created); };
  }, [id, token]);

  if (error) return <p role="alert" className="lv-alert">{error}</p>;
  if (!url) return <p className="lv-muted">Đang mở tệp…</p>;
  if (type === "pdf") return <iframe className="lv-viewer lv-viewer--pdf" src={url} title={title} />;
  if (type === "mp3" || type === "wav") return <audio controls src={url} />;
  return <img className="lv-viewer" src={url} alt={title} />;
}
