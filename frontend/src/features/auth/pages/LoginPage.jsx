import { useRef, useState } from "react";

import { googleLogin } from "../api/googleLogin.js";
import { login } from "../api/login.js";
import AuthField from "../components/AuthField.jsx";
import AuthShell from "../components/AuthShell.jsx";
import GoogleLinkForm from "../components/GoogleLinkForm.jsx";
import GoogleSignInButton from "../components/GoogleSignInButton.jsx";
import ResendVerificationButton from "../components/ResendVerificationButton.jsx";

const EMAIL_PATTERN = /^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/;

function validate(email, password) {
  const errors = {};
  if (!email) errors.email = "Nhập email của bạn.";
  else if (!EMAIL_PATTERN.test(email)) errors.email = "Email chưa đúng định dạng, ví dụ: ban@example.com.";
  if (!password) errors.password = "Nhập mật khẩu.";
  return errors;
}

export default function LoginPage({ onLogin, onGoForgotPassword }) {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [fieldErrors, setFieldErrors] = useState({});
  const [error, setError] = useState("");
  const [needsVerification, setNeedsVerification] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [pendingGoogleCredential, setPendingGoogleCredential] = useState("");
  const [mood, setMood] = useState("");
  const [tilt, setTilt] = useState(0);
  const submittingRef = useRef(false);
  const emailRef = useRef(null);
  const passwordRef = useRef(null);

  function showSad() {
    setMood("");
    requestAnimationFrame(() => setMood("sad"));
  }

  async function handleSubmit(event) {
    event.preventDefault();
    if (submittingRef.current) return;

    const trimmedEmail = email.trim();
    const errors = validate(trimmedEmail, password);
    setFieldErrors(errors);
    if (errors.email || errors.password) {
      (errors.email ? emailRef : passwordRef).current?.focus();
      showSad();
      return;
    }

    submittingRef.current = true;
    setSubmitting(true);
    setError("");
    setNeedsVerification(false);
    try {
      const data = await login(trimmedEmail, password);
      setPassword("");
      onLogin(data);
    } catch (err) {
      setError(err?.message || "Đăng nhập thất bại");
      setNeedsVerification(err?.code === "EMAIL_CHUA_XAC_MINH");
      showSad();
    } finally {
      submittingRef.current = false;
      setSubmitting(false);
    }
  }

  async function handleGoogleCredential(credential) {
    if (submittingRef.current || !credential) return;

    submittingRef.current = true;
    setSubmitting(true);
    setError("");
    setNeedsVerification(false);
    try {
      const data = await googleLogin(credential);
      onLogin(data);
    } catch (err) {
      if (err?.code === "CAN_LIEN_KET_TAI_KHOAN") {
        setPendingGoogleCredential(credential); // Chỉ giữ trong bộ nhớ, không lưu trình duyệt
        return;
      }
      setError(err?.message || "Đăng nhập Google thất bại");
      showSad();
    } finally {
      submittingRef.current = false;
      setSubmitting(false);
    }
  }

  if (pendingGoogleCredential) {
    return (
      <AuthShell mode="login">
        <div className="xa-legacy">
          <GoogleLinkForm
            credential={pendingGoogleCredential}
            onLinked={onLogin}
            onGoForgotPassword={onGoForgotPassword}
            onCancel={(message) => {
              setPendingGoogleCredential("");
              setError(message);
            }}
          />
        </div>
      </AuthShell>
    );
  }

  return (
    <AuthShell mode="login" mood={mood} tilt={tilt}>
      <section aria-labelledby="login-title">
        <h1 id="login-title">Chào mừng trở lại</h1>
        <p className="lead">Tiếp tục hành trình HSK cùng Xiang.</p>

        {error && (
          <div className={needsVerification ? "alert warn" : "alert bad"} role="alert">
            <svg className="ico" aria-hidden="true"><use href="#i-alert" /></svg>
            <div>
              {error}
              {needsVerification && (
                <div className="xa-legacy" style={{ marginTop: 8 }}>
                  <ResendVerificationButton email={email} />
                </div>
              )}
            </div>
          </div>
        )}

        <div className="gwrap">
          <GoogleSignInButton onCredential={handleGoogleCredential} disabled={submitting} />
        </div>
        <div className="or">hoặc dùng email</div>

        <form onSubmit={handleSubmit} noValidate>
          <AuthField
            id="login-email"
            label="Email"
            icon="i-mail"
            type="email"
            inputMode="email"
            autoComplete="username"
            placeholder="ban@example.com"
            value={email}
            inputRef={emailRef}
            error={fieldErrors.email}
            disabled={submitting}
            onChange={(e) => {
              setEmail(e.target.value);
              setTilt(-6 + Math.min(e.target.value.length, 28) * 0.5);
              if (fieldErrors.email) setFieldErrors((f) => ({ ...f, email: "" }));
            }}
            onBlur={() => setTilt(0)}
          />
          <AuthField
            id="login-password"
            label="Mật khẩu"
            icon="i-key"
            password
            autoComplete="current-password"
            placeholder="Mật khẩu của bạn"
            value={password}
            inputRef={passwordRef}
            error={fieldErrors.password}
            disabled={submitting}
            onChange={(e) => {
              setPassword(e.target.value);
              if (fieldErrors.password) setFieldErrors((f) => ({ ...f, password: "" }));
            }}
            onFocus={() => setMood("shy")}
            onBlur={() => setMood("")}
          />
          {onGoForgotPassword && (
            <div className="row-between">
              <button type="button" className="link" onClick={onGoForgotPassword} disabled={submitting}>
                Quên mật khẩu?
              </button>
            </div>
          )}
          <button className="btn coral block" type="submit" disabled={submitting}>
            {submitting ? (<><span className="spinner" aria-hidden="true"></span>Đang đăng nhập…</>) : "Đăng nhập"}
          </button>
        </form>
      </section>
    </AuthShell>
  );
}
