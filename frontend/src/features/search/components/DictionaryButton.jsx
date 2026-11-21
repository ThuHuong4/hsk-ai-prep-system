import { useCallback, useEffect, useState } from "react";

import DictionaryDialog from "./DictionaryDialog.jsx";

// Nút kính lúp mở bảng Tra từ; phím tắt "/" mở nhanh khi không đang gõ ở ô khác
export default function DictionaryButton({ className = "" }) {
  const [open, setOpen] = useState(false);
  const close = useCallback(() => setOpen(false), []);

  useEffect(() => {
    const onKey = (e) => {
      const tag = (e.target?.tagName || "").toLowerCase();
      if (e.key === "/" && !open && !["input", "textarea", "select"].includes(tag) && !e.target?.isContentEditable) {
        e.preventDefault();
        setOpen(true);
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open]);

  return (
    <>
      <button type="button" className={`dict-open ${className}`} onClick={() => setOpen(true)} aria-label="Tra từ" title="Tra từ (phím /)">
        <svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="11" cy="11" r="7" /><path d="m20 20-3.5-3.5" /></svg>
        <span>Tra từ</span>
      </button>
      {open && <DictionaryDialog onClose={close} />}
    </>
  );
}
