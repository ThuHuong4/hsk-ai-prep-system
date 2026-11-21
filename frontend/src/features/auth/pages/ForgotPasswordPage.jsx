import { useEffect, useRef, useState } from "react";

import { requestPasswordReset } from "../api/requestPasswordReset.js";
import AuthCard, { Notice } from "../components/AuthCard.jsx";
import AuthField from "../components/AuthField.jsx";

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

  let submitLabel = "Gửi liên kết đặt lại mật khẩu";
  if (submitting) submitLabel = "Đang gửi...";
  else if (cooldown > 0) submitLabel = `Gửi lại sau ${cooldown}s`;

  return (
    <AuthCard title="Quên mật khẩu?" lead="Nhập email đã đăng ký, Xiang sẽ gửi liên kết để bạn đặt mật khẩu mới.">
      {error && <Notice kind="bad">{error}</Notice>}
      {message && <Notice kind="ok">{message}</Notice>}
      <form onSubmit={handleSubmit} noValidate>
        <AuthField id="forgot-email" label="Email" icon="i-mail" type="email" inputMode="email" autoComplete="email"
          placeholder="ban@example.com" maxLength={255} value={email} onChange={(e) => setEmail(e.target.value)} disabled={submitting} />
        <button className="btn block" type="submit" disabled={submitting || cooldown > 0}>{submitLabel}</button>
      </form>
      <p className="ac-alt" style={{ marginTop: 18 }}>
        Nhớ ra rồi? <button type="button" className="link" onClick={onGoLogin} disabled={submitting}>Quay lại đăng nhập</button>
      </p>
    </AuthCard>
  );
}
