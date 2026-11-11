import { useRef, useState } from "react";

import { resetPassword } from "../api/resetPassword.js";
import { validatePassword } from "../utils/passwordPolicy.js";

const TOKEN_ERROR_CODES = ["TOKEN_KHONG_HOP_LE", "TOKEN_HET_HAN", "TOKEN_DA_DUNG"];

export default function ResetPasswordPage({ token, onGoLogin, onGoForgotPassword }) {
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [error, setError] = useState("");
  const [errorCode, setErrorCode] = useState(null);
  const [doneMessage, setDoneMessage] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const submittingRef = useRef(false);

  async function handleSubmit(event) {
    event.preventDefault();
    if (submittingRef.current) return;

    if (!password || !confirmPassword) {
      setError("Vui lòng nhập mật khẩu mới và nhập lại");
      return;
    }
    const passwordError = validatePassword(password);
    if (passwordError) {
      setError(passwordError);
      return;
    }
    if (password !== confirmPassword) {
      setError("Mật khẩu nhập lại không khớp");
      return;
    }

    submittingRef.current = true;
    setSubmitting(true);
    setError("");
    setErrorCode(null);
    try {
      const data = await resetPassword(token, password);
      setPassword("");
      setConfirmPassword("");
      setDoneMessage(data.message);
    } catch (err) {
      setError(err?.message || "Không đặt lại được mật khẩu, vui lòng thử lại");
      setErrorCode(err?.code ?? null);
    } finally {
      submittingRef.current = false;
      setSubmitting(false);
    }
  }

  const goButtons = (
    <>
      <button type="button" onClick={onGoForgotPassword}>Yêu cầu liên kết mới</button>
      <button type="button" onClick={onGoLogin}>Đến trang đăng nhập</button>
    </>
  );

  if (!token) {
    return (
      <div>
        <h1>Đặt lại mật khẩu</h1>
        <p role="alert">Liên kết đặt lại mật khẩu không hợp lệ hoặc bị thiếu mã.</p>
        {goButtons}
      </div>
    );
  }

  if (doneMessage) {
    return (
      <div>
        <h1>Đặt lại mật khẩu</h1>
        <p role="status">{doneMessage}</p>
        <button type="button" onClick={onGoLogin}>Đăng nhập</button>
      </div>
    );
  }

  if (TOKEN_ERROR_CODES.includes(errorCode)) {
    return (
      <div>
        <h1>Đặt lại mật khẩu</h1>
        <p role="alert">{error}</p>
        {goButtons}
      </div>
    );
  }

  return (
    <form onSubmit={handleSubmit} noValidate>
      <h1>Đặt mật khẩu mới</h1>

      <label htmlFor="reset-password">Mật khẩu mới</label>
      <input
        id="reset-password"
        type="password"
        autoComplete="new-password"
        value={password}
        onChange={(e) => setPassword(e.target.value)}
        disabled={submitting}
        maxLength={128}
        required
      />
      <small>Từ 8 đến 128 ký tự, có ít nhất 1 chữ cái và 1 chữ số.</small>

      <label htmlFor="reset-confirm-password">Nhập lại mật khẩu mới</label>
      <input
        id="reset-confirm-password"
        type="password"
        autoComplete="new-password"
        value={confirmPassword}
        onChange={(e) => setConfirmPassword(e.target.value)}
        disabled={submitting}
        maxLength={128}
        required
      />

      {error && <p role="alert">{error}</p>}

      <button type="submit" disabled={submitting}>
        {submitting ? "Đang lưu..." : "Đặt mật khẩu mới"}
      </button>
    </form>
  );
}