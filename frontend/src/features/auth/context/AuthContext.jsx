import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";

import { http } from "../../../shared/api/httpClient.js";

const AuthContext = createContext(null);
// Giữ đăng nhập khi tải lại trang; đóng tab thì mất (sessionStorage). Chỉ lưu token, không lưu thông tin khác.
const TOKEN_KEY = "xianglingo-token";

function readToken() {
  try {
    return sessionStorage.getItem(TOKEN_KEY);
  } catch {
    return null;
  }
}

function writeToken(value) {
  try {
    if (value) sessionStorage.setItem(TOKEN_KEY, value);
    else sessionStorage.removeItem(TOKEN_KEY);
  } catch {
    // trình duyệt chặn lưu trữ: vẫn đăng nhập được, chỉ mất khi tải lại
  }
}

export function AuthProvider({ children }) {
  const [token, setToken] = useState(readToken);
  const [user, setUser] = useState(null);
  // có token đã lưu → hỏi lại máy chủ xem còn hợp lệ không trước khi cho vào trang cần đăng nhập
  const [checking, setChecking] = useState(() => Boolean(readToken()));

  useEffect(() => {
    const saved = readToken();
    if (!saved) return undefined;
    const controller = new AbortController();
    http.get("/api/auth/me", { token: saved, signal: controller.signal })
      .then((me) => setUser(me))
      .catch((error) => {
        if (error.name === "AbortError") return;
        writeToken(null);
        setToken(null);
      })
      .finally(() => {
        if (!controller.signal.aborted) setChecking(false);
      });
    return () => controller.abort();
  }, []);

  const login = useCallback((data) => {
    if (!data?.access_token || !data?.user) {
      throw new Error("Phản hồi đăng nhập không hợp lệ");
    }
    writeToken(data.access_token);
    setToken(data.access_token);
    setUser(data.user);
    setChecking(false);
  }, []);

  // Gọi sau khi xác minh email thành công để ẩn thanh nhắc
  const markEmailVerified = useCallback(() => {
    setUser((current) => (current ? { ...current, email_da_xac_minh: true } : current));
  }, []);

  const logout = useCallback(() => {
    writeToken(null);
    setToken(null);
    setUser(null);
  }, []);

  const value = useMemo(
    () => ({ token, user, checking, isAuthenticated: Boolean(token && user), login, logout, markEmailVerified }),
    [token, user, checking, login, logout, markEmailVerified]
  );

  // Đang khôi phục đăng nhập: chưa vẽ trang để không bị đẩy về trang đăng nhập hay hiện giao diện Khách
  return (
    <AuthContext.Provider value={value}>
      {checking ? <p className="auth-restoring" role="status" style={{ padding: 24 }}>Đang tải...</p> : children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (context === null) {
    throw new Error("useAuth phải được dùng bên trong AuthProvider");
  }
  return context;
}
