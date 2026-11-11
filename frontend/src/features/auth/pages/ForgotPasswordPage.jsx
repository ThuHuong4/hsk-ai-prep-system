import { useEffect, useRef, useState } from "react";

import { requestPasswordReset } from "../api/requestPasswordReset.js";

const EMAIL_PATTERN = /^[^@\s]+@[^@\s]+\.[^@\s]+$/;
// Khớp AUTH_RESEND_MIN_SECONDS của backend; backend vẫn là nơi quyết định cuối cùng
const COOLDOWN_SECONDS = 60;

export default function ForgotPasswordPage({ onGoLogin }) {
  const [email, setEmail] = useState("");
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [cooldown, setCooldown] = useState(0);
  const submittingRef = useRef(false);

  useEffect(() => {
    if (cooldown <= 0) return undefined;
    const timerId = setTimeout(() => setCooldown((seconds) => seconds - 1), 1000);
    return () => clearTimeout(timerId);
  }, [cooldown]);

  async function handleSubmit(event) {
    event.preventDefault();
    if (submittingRef.current || cooldown > 0) return;

    const trimmedEmail = email.trim();
    if (!EMAIL_PATTERN.test(trimmedEmail)) {
      setError("Vui lòng nhập email hợp lệ");
      return;
    }

    submittingRef.current = true;
    setSubmitting(true);
    setError("");
    setMessage("");
    try {
      const data = await requestPasswordReset(trimmedEmail);
      setMessage(data.message);
      setCooldown(COOLDOWN_SECONDS);
    } catch (err) {
      setError(err?.message || "Không gửi được yêu cầu, vui lòng thử lại");
      if (err?.retryAfterSeconds) setCooldown(err.retryAfterSeconds);
    } finally {
      submittingRef.current = false;
      setSubmitting(false);
    }
  }

  let submitLabel = "Gửi hướng dẫn đặt lại mật khẩu";
  if (submitting) submitLabel = "Đang gửi...";
  else if (cooldown > 0) submitLabel = `Gửi lại (${cooldown}s)`;

  return (
    <form onSubmit={handleSubmit} noValidate>
      <h1>Quên mật khẩu</h1>
      <p>Nhập email đã đăng ký để nhận liên kết đặt lại mật khẩu.</p>

      <label htmlFor="forgot-email">Email</label>
      <input
        id="forgot-email"
        type="email"
        autoComplete="email"
        value={email}
        onChange={(e) => setEmail(e.target.value)}
        disabled={submitting}
        maxLength={255}
        required
      />

      {error && <p role="alert">{error}</p>}
      {message && <p role="status">{message}</p>}

      <button type="submit" disabled={submitting || cooldown > 0}>
        {submitLabel}
      </button>
      <button type="button" onClick={onGoLogin} disabled={submitting}>
        Quay lại đăng nhập
      </button>
    </form>
  );
}