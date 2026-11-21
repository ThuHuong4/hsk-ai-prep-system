import { useEffect, useRef, useState } from "react";

import { resendVerification } from "../api/resendVerification.js";
import { useAuth } from "../context/AuthContext.jsx";

// Khớp AUTH_RESEND_MIN_SECONDS của backend; backend vẫn là nơi quyết định cuối cùng
const DEFAULT_COOLDOWN_SECONDS = 60;

export default function ResendVerificationButton() {
  const { token, markEmailVerified } = useAuth();
  const [cooldown, setCooldown] = useState(0);
  const [sending, setSending] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const sendingRef = useRef(false);

  useEffect(() => {
    if (cooldown <= 0) return undefined;
    const timerId = setTimeout(() => setCooldown((seconds) => seconds - 1), 1000);
    return () => clearTimeout(timerId);
  }, [cooldown]);

  async function handleClick() {
    if (!token || sendingRef.current || cooldown > 0) return;
    sendingRef.current = true;
    setSending(true);
    setMessage("");
    setError("");
    try {
      const data = await resendVerification(token);
      setMessage(data.message);
      setCooldown(DEFAULT_COOLDOWN_SECONDS);
    } catch (err) {
      if (err?.code === "DA_XAC_MINH") {
        markEmailVerified(); // Đã xác minh ở tab khác: ẩn thanh nhắc
        return;
      }
      setError(err?.message || "Không gửi được, vui lòng thử lại");
      if (err?.retryAfterSeconds) setCooldown(err.retryAfterSeconds);
    } finally {
      sendingRef.current = false;
      setSending(false);
    }
  }

  let label = "Gửi thư xác minh";
  if (sending) label = "Đang gửi...";
  else if (cooldown > 0) label = `Gửi lại (${cooldown}s)`;

  return (
    <span className="verify-banner__action">
      <button type="button" onClick={handleClick} disabled={sending || cooldown > 0}>
        {label}
      </button>
      {message && <span role="status">{message}</span>}
      {error && <span role="alert">{error}</span>}
    </span>
  );
}
