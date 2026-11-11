import { useRef, useState } from "react";

import { linkGoogleAccount } from "../api/linkGoogleAccount.js";

export default function GoogleLinkForm({ credential, onLinked, onCancel, onGoForgotPassword }) {
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const submittingRef = useRef(false);

  async function handleSubmit(event) {
    event.preventDefault();
    if (submittingRef.current) return;
    if (!password) {
      setError("Vui lòng nhập mật khẩu");
      return;
    }

    submittingRef.current = true;
    setSubmitting(true);
    setError("");
    try {
      const data = await linkGoogleAccount(credential, password);
      setPassword("");
      onLinked(data);
    } catch (err) {
      setPassword("");
      if (err?.code === "GOOGLE_TOKEN_KHONG_HOP_LE") {
        onCancel(err.message); // Credential hết hạn: quay lại để bấm Google lần nữa
        return;
      }
      setError(err?.message || "Không liên kết được tài khoản, vui lòng thử lại");
    } finally {
      submittingRef.current = false;
      setSubmitting(false);
    }
  }

  return (
    <form onSubmit={handleSubmit} noValidate>
      <h1>Liên kết tài khoản Google</h1>
      <p>
        Email Google của bạn đã có tài khoản HSK AI. Nhập mật khẩu của tài khoản HSK AI để xác nhận
        và liên kết. Sau khi liên kết, bạn đăng nhập được bằng cả mật khẩu và Google.
      </p>

      <label htmlFor="link-password">Mật khẩu tài khoản HSK AI</label>
      <input
        id="link-password"
        type="password"
        autoComplete="current-password"
        value={password}
        onChange={(e) => setPassword(e.target.value)}
        disabled={submitting}
        maxLength={128}
        required
      />

      {error && <p role="alert">{error}</p>}

      <button type="submit" disabled={submitting}>
        {submitting ? "Đang liên kết..." : "Xác nhận và liên kết"}
      </button>
      <button type="button" onClick={() => onCancel("")} disabled={submitting}>
        Hủy
      </button>
      {onGoForgotPassword && (
        <button type="button" onClick={onGoForgotPassword} disabled={submitting}>
          Quên mật khẩu?
        </button>
      )}
    </form>
  );
}