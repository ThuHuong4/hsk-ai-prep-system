import { useEffect, useRef, useState } from "react";

import { resendVerification } from "../api/resendVerification.js";

// Khớp AUTH_RESEND_MIN_SECONDS của backend; backend vẫn là nơi quyết định cuối cùng
const DEFAULT_COOLDOWN_SECONDS = 60;

export default function ResendVerificationButton({ email, initialCooldown = 0 }) {
  const [cooldown, setCooldown] = useState(initialCooldown);
  const [sending, setSending] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const sendingRef = useRef(false);

  useEffect(() => {
    if (cooldown <= 0) return undefined;
    const timerId = setTimeout(() => setCooldown((seconds) => seconds - 1), 1000);
    return () => clearTimeout(timerId);
  }, [cooldown]);

  const trimmedEmail = (email || "").trim();

  async function handleClick() {
    if (!trimmedEmail || sendingRef.current || cooldown > 0) return;

    sendingRef.current = true;
    setSending(true);
    setMessage("");
    setError("");
    try {
      const data = await resendVerification(trimmedEmail);
      setMessage(data.message);
      setCooldown(DEFAULT_COOLDOWN_SECONDS);
    } catch (err) {
      setError(err?.message || "Không gửi lại được, vui lòng thử lại");
      if (err?.retryAfterSeconds) setCooldown(err.retryAfterSeconds);
    } finally {
      sendingRef.current = false;
      setSending(false);
    }
  }

  let label = "Gửi lại email xác minh";
  if (sending) label = "Đang gửi...";
  else if (cooldown > 0) label = `Gửi lại email xác minh (${cooldown}s)`;

  return (
    <div>
      <button
        type="button"
        onClick={handleClick}
        disabled={sending || cooldown > 0 || !trimmedEmail}
      >
        {label}
      </button>
      {message && <p role="status">{message}</p>}
      {error && <p role="alert">{error}</p>}
    </div>
  );
}