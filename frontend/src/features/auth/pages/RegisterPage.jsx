import { googleLogin } from "../api/googleLogin.js";
import GoogleSignInButton from "../components/GoogleSignInButton.jsx";
import GoogleLinkForm from "../components/GoogleLinkForm.jsx";
import { useRef, useState } from "react";

import { register } from "../api/register.js";
import AuthField from "../components/AuthField.jsx";
import AuthShell from "../components/AuthShell.jsx";
import ResendVerificationButton from "../components/ResendVerificationButton.jsx";
import { PASSWORD_MAX_LENGTH, PASSWORD_MIN_LENGTH, validatePassword } from "../utils/passwordPolicy.js";

const EMAIL_PATTERN = /^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/;
const VERIFY_EMAIL_COOLDOWN_SECONDS = 60;
const FIELD_ORDER = ["hoTen", "email", "password", "confirmPassword"];

const RULES = [
  { key: "len", label: `${PASSWORD_MIN_LENGTH}–${PASSWORD_MAX_LENGTH} ký tự`, test: (p) => p.length >= PASSWORD_MIN_LENGTH && p.length <= PASSWORD_MAX_LENGTH },
  { key: "letter", label: "Có chữ cái", test: (p) => /\p{L}/u.test(p) },
  { key: "digit", label: "Có chữ số", test: (p) => /\d/.test(p) },
];

function validate({ hoTen, email, password, confirmPassword }) {
  const errors = {};
  const name = hoTen.trim();
  const mail = email.trim();
  if (!name) errors.hoTen = "Nhập họ và tên.";
  else if (name.length > 100) errors.hoTen = "Họ tên tối đa 100 ký tự.";
  if (!mail) errors.email = "Nhập email.";
  else if (!EMAIL_PATTERN.test(mail)) errors.email = "Email chưa đúng định dạng, ví dụ: ban@example.com.";
  if (!password) errors.password = "Tạo mật khẩu.";
  else {
    const passwordError = validatePassword(password);
    if (passwordError) errors.password = `${passwordError}.`;
  }
  if (!confirmPassword) errors.confirmPassword = "Nhập lại mật khẩu.";
  else if (confirmPassword !== password) errors.confirmPassword = "Hai mật khẩu chưa giống nhau.";
  return errors;
}

export default function RegisterPage({
  onGoLogin,
  onLogin,
  onGoForgotPassword,
}) {
  const [values, setValues] = useState({ hoTen: "", email: "", password: "", confirmPassword: "" });
  const [fieldErrors, setFieldErrors] = useState({});
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [doneMessage, setDoneMessage] = useState("");
  const [submittedEmail, setSubmittedEmail] = useState("");
  const [mood, setMood] = useState("");
  const [tilt, setTilt] = useState(0);
  const [pendingGoogleCredential, setPendingGoogleCredential] = useState("");

  const submittingRef = useRef(false);
  const refs = { hoTen: useRef(null), email: useRef(null), password: useRef(null), confirmPassword: useRef(null) };

  function showMood(next) {
    setMood("");
    requestAnimationFrame(() => setMood(next));
  }

  function bind(name) {
    return {
      value: values[name],
      inputRef: refs[name],
      error: fieldErrors[name],
      disabled: submitting,
      onChange: (e) => {
        const v = e.target.value;
        setValues((s) => ({ ...s, [name]: v }));
        if (name === "hoTen" || name === "email") setTilt(-6 + Math.min(v.length, 28) * 0.5);
        if (fieldErrors[name]) setFieldErrors((f) => ({ ...f, [name]: "" }));
      },
      onBlur: () => { setTilt(0); if (name === "password" || name === "confirmPassword") setMood(""); },
      onFocus: name === "password" || name === "confirmPassword" ? () => setMood("shy") : undefined,
    };
  }

  async function handleSubmit(event) {
    event.preventDefault();
    if (submittingRef.current) return;

    const errors = validate(values);
    setFieldErrors(errors);
    const firstBad = FIELD_ORDER.find((k) => errors[k]);
    if (firstBad) {
      refs[firstBad].current?.focus();
      showMood("sad");
      return;
    }

    submittingRef.current = true;
    setSubmitting(true);
    setError("");
    try {
      const data = await register(values.hoTen.trim(), values.email.trim(), values.password);
      setSubmittedEmail(values.email.trim());
      setDoneMessage(data.message);
      setValues((s) => ({ ...s, password: "", confirmPassword: "" }));
      showMood("happy");
    } catch (err) {
      setError(err?.message || "Đăng ký thất bại, vui lòng thử lại");
      showMood("sad");
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

  try {
    const data = await googleLogin(credential);
    onLogin(data);
  } catch (err) {
    if (err?.code === "CAN_LIEN_KET_TAI_KHOAN") {
      setPendingGoogleCredential(credential);
    } else {
      setError(err?.message || "Không thể tiếp tục với Google.");
      showMood("sad");
    }
  } finally {
    submittingRef.current = false;
    setSubmitting(false);
  }
}

if (pendingGoogleCredential) {
  return (
    <AuthShell mode="reg">
      <div className="xa-legacy">
        <GoogleLinkForm
          credential={pendingGoogleCredential}
          onLinked={onLogin}
          onGoForgotPassword={onGoForgotPassword}
          onCancel={(message) => {
            setPendingGoogleCredential("");
            setError(message || "");
          }}
        />
      </div>
    </AuthShell>
  );
}
  return (
    <AuthShell mode="reg" mood={mood} tilt={tilt}>
      <section aria-labelledby="reg-title">
        <h1 id="reg-title">{doneMessage ? "Kiểm tra email của bạn" : "Tạo tài khoản"}</h1>
        <p className="lead">{doneMessage ? "Còn một bước nữa là bắt đầu học." : "Miễn phí. Tài khoản mới là tài khoản Học viên."}</p>

        {doneMessage ? (
          <>
            <div className="alert ok" role="status">
              <svg className="ico" aria-hidden="true"><use href="#i-check" /></svg>
              <div>{doneMessage}</div>
            </div>
            <div className="xa-legacy">
              <ResendVerificationButton email={submittedEmail} initialCooldown={VERIFY_EMAIL_COOLDOWN_SECONDS} />
            </div>
            <button type="button" className="btn coral block" style={{ marginTop: 16 }} onClick={onGoLogin}>
              Đến trang đăng nhập
            </button>
          </>
        ) : (
          <>
            {error && (
              <div className="alert bad" role="alert">
                <svg className="ico" aria-hidden="true"><use href="#i-alert" /></svg>
                <div>{error}</div>
              </div>
            )}
            <div className="gwrap">
              <GoogleSignInButton
                onCredential={handleGoogleCredential}
                disabled={submitting}
              />
            </div>

            <div className="or">HOẶC DÙNG EMAIL</div>
            <form onSubmit={handleSubmit} noValidate>
              <AuthField id="register-name" label="Họ và tên" icon="i-id" autoComplete="name" placeholder="Nguyễn Văn A" maxLength={100} {...bind("hoTen")} />
              <AuthField id="register-email" label="Email" icon="i-mail" type="email" inputMode="email" autoComplete="email" placeholder="ban@example.com" maxLength={255} {...bind("email")} />
              <AuthField id="register-password" label="Mật khẩu" icon="i-key" password autoComplete="new-password" placeholder={`Ít nhất ${PASSWORD_MIN_LENGTH} ký tự`} maxLength={PASSWORD_MAX_LENGTH} describedBy="register-rules" {...bind("password")}>
                <ul className="rules" id="register-rules">
                  {RULES.map((r) => (
                    <li key={r.key} className={r.test(values.password) ? "ok" : undefined}>
                      <svg className="ico" aria-hidden="true"><use href="#i-check" /></svg>{r.label}
                    </li>
                  ))}
                </ul>
              </AuthField>
              <AuthField id="register-confirm-password" label="Nhập lại mật khẩu" icon="i-key" type="password" autoComplete="new-password" placeholder="Nhập lại mật khẩu" maxLength={PASSWORD_MAX_LENGTH} {...bind("confirmPassword")} />
              <button className="btn coral block" type="submit" disabled={submitting}>
                {submitting ? (<><span className="spinner" aria-hidden="true"></span>Đang tạo tài khoản…</>) : "Tạo tài khoản"}
              </button>
            </form>
          </>
        )}
      </section>
    </AuthShell>
  );
}
