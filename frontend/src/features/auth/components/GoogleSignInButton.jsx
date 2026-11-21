import { useEffect, useRef, useState } from "react";

const SCRIPT_SRC = "https://accounts.google.com/gsi/client";
let scriptPromise = null;

function loadGoogleScript() {
  if (window.google?.accounts?.id) return Promise.resolve();
  if (!scriptPromise) {
    scriptPromise = new Promise((resolve, reject) => {
      const script = document.createElement("script");
      script.src = SCRIPT_SRC;
      script.async = true;
      script.defer = true;
      script.onload = () => resolve();
      script.onerror = () => {
        scriptPromise = null; // Cho phép thử tải lại ở lần sau
        reject(new Error("Không tải được thư viện Google"));
      };
      document.head.appendChild(script);
    });
  }
  return scriptPromise;
}

export default function GoogleSignInButton({ onCredential, disabled = false }) {
  const clientId = import.meta.env.VITE_GOOGLE_CLIENT_ID;
  const containerRef = useRef(null);
  const callbackRef = useRef(onCredential);
  const [loadError, setLoadError] = useState("");

  callbackRef.current = onCredential;

  useEffect(() => {
    if (!clientId) return undefined;
    let cancelled = false;

    loadGoogleScript()
      .then(() => {
        if (cancelled || !containerRef.current) return;
        window.google.accounts.id.initialize({
          client_id: clientId,
          ux_mode: "popup",
          callback: (response) => callbackRef.current(response.credential),
        });
        // Nút theo chế độ sáng/tối, rộng bằng form (Google giới hạn 200–400px)
        const dark = document.documentElement.dataset.theme === "dark";
        const width = Math.max(200, Math.min(400, Math.round(containerRef.current.offsetWidth || 400)));
        window.google.accounts.id.renderButton(containerRef.current, {
          type: "standard",
          theme: dark ? "filled_black" : "outline",
          size: "large",
          text: "continue_with",
          shape: "pill",
          logo_alignment: "left",
          locale: "vi",
          width,
        });
      })
      .catch(() => {
        if (!cancelled) setLoadError("Không tải được Đăng nhập Google. Hãy kiểm tra kết nối mạng.");
      });

    return () => {
      cancelled = true;
    };
  }, [clientId]);

  if (!clientId) return <p role="alert">Chưa cấu hình VITE_GOOGLE_CLIENT_ID.</p>;
  if (loadError) return <p role="alert">{loadError}</p>;

  return (
    <div
      className="gbtn-slot"
      ref={containerRef}
      aria-disabled={disabled}
      style={disabled ? { pointerEvents: "none", opacity: 0.6 } : undefined}
    />
  );
}