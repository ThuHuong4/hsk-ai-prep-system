import { useRef, useState } from "react";

import { resetPassword } from "../api/resetPassword.js";
import AuthCard, { Notice } from "../components/AuthCard.jsx";
import AuthField from "../components/AuthField.jsx";
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
      <button className="btn block" type="button" onClick={onGoForgotPassword}>Yêu cầu liên kết mới</button>
      <button className="btn plain block" type="button" onClick={onGoLogin}>Đến trang đăng nhập</button>
    </>
  );

  if (!token) {
    return (
      <AuthCard title="Đặt lại mật khẩu">
        <Notice kind="bad">Liên kết đặt lại mật khẩu không hợp lệ hoặc bị thiếu mã.</Notice>
        {goButtons}
      </AuthCard>
    );
  }

  if (doneMessage) {
    return (
      <AuthCard title="Đã đặt mật khẩu mới">
        <Notice kind="ok">{doneMessage}</Notice>
        <button className="btn block" type="button" onClick={onGoLogin}>Đăng nhập</button>
      </AuthCard>
    );
  }

  if (TOKEN_ERROR_CODES.includes(errorCode)) {
    return (
      <AuthCard title="Đặt lại mật khẩu">
        <Notice kind="bad">{error}</Notice>
        {goButtons}
      </AuthCard>
    );
  }

  return (
    <AuthCard title="Đặt mật khẩu mới" lead="Chọn mật khẩu mới cho tài khoản Xianglingo của bạn.">
      {error && <Notice kind="bad">{error}</Notice>}
      <form onSubmit={handleSubmit} noValidate>
        <AuthField id="reset-password" label="Mật khẩu mới" icon="i-key" password autoComplete="new-password" placeholder="Ít nhất 8 ký tự"
          maxLength={128} value={password} onChange={(e) => setPassword(e.target.value)} disabled={submitting} describedBy="reset-rule">
          <p className="hint" id="reset-rule">Từ 8 đến 128 ký tự, có ít nhất 1 chữ cái và 1 chữ số.</p>
        </AuthField>
        <AuthField id="reset-confirm-password" label="Nhập lại mật khẩu mới" icon="i-key" type="password" autoComplete="new-password"
          placeholder="Nhập lại mật khẩu" maxLength={128} value={confirmPassword} onChange={(e) => setConfirmPassword(e.target.value)} disabled={submitting} />
        <button className="btn coral block" type="submit" disabled={submitting}>{submitting ? "Đang lưu..." : "Đặt mật khẩu mới"}</button>
      </form>
    </AuthCard>
  );
}
