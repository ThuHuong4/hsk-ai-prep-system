import { useNavigate } from "react-router-dom";

import "../styles/scrollNav.css";

// Nút mũi tên Quay lại ở góc trên bên trái: nếu truyền `to` thì đi thẳng tới đích đó; ngược lại về trang trước (hoặc `home`).
export default function BackButton({ home = "/", to = null, className = "" }) {
  const navigate = useNavigate();
  const back = () => {
    if (to) navigate(to);
    else if ((window.history.state?.idx ?? 0) > 0) navigate(-1);
    else navigate(home);
  };
  return (
    <button type="button" className={className} onClick={back} aria-label="Quay lại trang trước" title="Quay lại">
      <svg viewBox="0 0 24 24" width="20" height="20" aria-hidden="true" fill="none" stroke="currentColor" strokeWidth="2.4"
        strokeLinecap="round" strokeLinejoin="round"><path d="M19 12H5M11 6l-6 6 6 6" /></svg>
    </button>
  );
}
