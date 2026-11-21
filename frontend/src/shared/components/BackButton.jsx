import { useNavigate } from "react-router-dom";

import "../styles/scrollNav.css";

// Nút mũi tên Quay lại ở góc trên bên trái: về trang trước; mở thẳng bằng đường dẫn (không có trang trước) thì về home.
export default function BackButton({ home = "/", className = "" }) {
  const navigate = useNavigate();
  const back = () => ((window.history.state?.idx ?? 0) > 0 ? navigate(-1) : navigate(home));
  return (
    <button type="button" className={className} onClick={back} aria-label="Quay lại trang trước" title="Quay lại">
      <svg viewBox="0 0 24 24" width="20" height="20" aria-hidden="true" fill="none" stroke="currentColor" strokeWidth="2.4"
        strokeLinecap="round" strokeLinejoin="round"><path d="M19 12H5M11 6l-6 6 6 6" /></svg>
    </button>
  );
}
