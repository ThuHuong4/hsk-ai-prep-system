import { useState } from "react";

// Ô nhập theo bản mô phỏng: biểu tượng đầu dòng, lỗi riêng từng ô, nút ẩn/hiện mật khẩu
export default function AuthField({
  id, label, icon, type = "text", value, onChange, error, password = false,
  describedBy, inputRef, children, ...inputProps
}) {
  const [show, setShow] = useState(false);
  const errId = `${id}-err`;
  const describedIds = [describedBy, error ? errId : null].filter(Boolean).join(" ") || undefined;

  return (
    <div className="field">
      <label htmlFor={id}>{label}</label>
      <div className={password ? "input has-eye" : "input"}>
        <svg className="ico lead-ico" aria-hidden="true"><use href={`#${icon}`} /></svg>
        <input
          id={id}
          ref={inputRef}
          type={password ? (show ? "text" : "password") : type}
          value={value}
          onChange={onChange}
          aria-invalid={error ? "true" : undefined}
          aria-describedby={describedIds}
          {...inputProps}
        />
        {password && (
          <button
            type="button"
            className="eye"
            onClick={() => setShow((s) => !s)}
            aria-label={show ? "Ẩn mật khẩu" : "Hiện mật khẩu"}
            aria-pressed={show}
          >
            <svg className="ico" aria-hidden="true"><use href={show ? "#i-eyeoff" : "#i-eye"} /></svg>
          </button>
        )}
      </div>
      {children}
      {error && (
        <div className="err" id={errId}>
          <svg className="ico" aria-hidden="true"><use href="#i-alert" /></svg>
          <span>{error}</span>
        </div>
      )}
    </div>
  );
}
