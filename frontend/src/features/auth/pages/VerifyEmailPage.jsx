import { useRef, useState } from "react";

import { verifyEmail } from "../api/verifyEmail.js";
import ResendVerificationButton from "../components/ResendVerificationButton.jsx";

export default function VerifyEmailPage({ token, onGoLogin }) {
  // missing | ready | verifying | success | error
  const [status, setStatus] = useState(token ? "ready" : "missing");
  const [message, setMessage] = useState("");
  const [errorCode, setErrorCode] = useState(null);
  const [email, setEmail] = useState("");
  const verifyingRef = useRef(false);

  async function handleVerify() {
    if (verifyingRef.current || !token) return;
    verifyingRef.current = true;
    setStatus("verifying");
    setMessage("");
    setErrorCode(null);
    try {
      const data = await verifyEmail(token);
      setMessage(data.message);
      setStatus("success");
    } catch (err) {
      setErrorCode(err?.code ?? null);
      setMessage(err?.message || "Không xác minh được email, vui lòng thử lại");
      setStatus("error");
    } finally {
      verifyingRef.current = false;
    }
  }

  const resendSection = (
    <div>
      <p>Nhập email đã đăng ký để nhận liên kết xác minh mới:</p>
      <label htmlFor="verify-resend-email">Email</label>
      <input
        id="verify-resend-email"
        type="email"
        autoComplete="email"
        value={email}
        onChange={(e) => setEmail(e.target.value)}
        maxLength={255}
      />
      <ResendVerificationButton email={email} />
    </div>
  );

  return (
    <div>
      <h1>Xác minh email</h1>

      {status === "missing" && (
        <>
          <p role="alert">Liên kết xác minh không hợp lệ hoặc bị thiếu mã.</p>
          {resendSection}
        </>
      )}

      {(status === "ready" || status === "verifying") && (
        <>
          <p>Bấm nút dưới đây để hoàn tất xác minh email.</p>
          <button type="button" onClick={handleVerify} disabled={status === "verifying"}>
            {status === "verifying" ? "Đang xác minh..." : "Xác minh email"}
          </button>
        </>
      )}

      {status === "success" && <p role="status">{message}</p>}

      {status === "error" && (
        <>
          <p role="alert">{message}</p>
          {errorCode === null && (
            <button type="button" onClick={handleVerify}>
              Thử lại
            </button>
          )}
          {(errorCode === "TOKEN_HET_HAN" || errorCode === "TOKEN_KHONG_HOP_LE") && resendSection}
        </>
      )}

      <button type="button" onClick={onGoLogin}>
        Đến trang đăng nhập
      </button>
    </div>
  );
}