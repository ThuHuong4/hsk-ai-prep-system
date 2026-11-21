import { useRef, useState } from "react";

import { verifyEmail } from "../api/verifyEmail.js";
import AuthCard, { Notice } from "../components/AuthCard.jsx";
import { useAuth } from "../context/AuthContext.jsx";

export default function VerifyEmailPage({ token, onDone }) {
  const { user, markEmailVerified } = useAuth();
  // missing | ready | verifying | success | error
  const [status, setStatus] = useState(token ? "ready" : "missing");
  const [message, setMessage] = useState("");
  const [errorCode, setErrorCode] = useState(null);
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
      markEmailVerified();
    } catch (err) {
      setErrorCode(err?.code ?? null);
      setMessage(err?.message || "Không xác minh được email, vui lòng thử lại");
      setStatus("error");
      if (err?.code === "TOKEN_DA_DUNG") markEmailVerified();
    } finally {
      verifyingRef.current = false;
    }
  }

  const resendHint = (
    <p className="ac-alt" style={{ marginBottom: 16 }}>
      {user
        ? "Bấm “Gửi thư xác minh” trên thanh nhắc ở đầu trang để nhận liên kết mới."
        : "Hãy đăng nhập, rồi bấm “Gửi thư xác minh” trên thanh nhắc ở đầu trang để nhận liên kết mới."}
    </p>
  );

  return (
    <AuthCard title="Xác minh email" lead={status === "ready" || status === "verifying" ? "Bấm nút dưới đây để hoàn tất xác minh email." : null}>
      {status === "missing" && (
        <>
          <Notice kind="bad">Liên kết xác minh không hợp lệ hoặc bị thiếu mã.</Notice>
          {resendHint}
        </>
      )}

      {(status === "ready" || status === "verifying") && (
        <button className="btn block" type="button" onClick={handleVerify} disabled={status === "verifying"}>
          {status === "verifying" ? "Đang xác minh..." : "Xác minh email"}
        </button>
      )}

      {status === "success" && <Notice kind="ok">{message}</Notice>}

      {status === "error" && (
        <>
          <Notice kind="bad">{message}</Notice>
          {errorCode === null && (
            <button className="btn block" type="button" onClick={handleVerify}>Thử lại</button>
          )}
          {(errorCode === "TOKEN_HET_HAN" || errorCode === "TOKEN_KHONG_HOP_LE") && resendHint}
        </>
      )}

      <button className={`btn block${status === "success" ? "" : " plain"}`} type="button" onClick={onDone} style={{ marginTop: 14 }}>
        {user ? "Tiếp tục học" : "Đến trang đăng nhập"}
      </button>
    </AuthCard>
  );
}
