export class HttpError extends Error {
  constructor(status, message, data = null, retryAfterSeconds = null) {
    super(message);
    this.name = "HttpError";
    this.status = status;
    this.data = data;
    const detail = data?.detail;
    this.code = detail && typeof detail === "object" && !Array.isArray(detail) ? detail.ma_loi ?? null : null;
    this.retryAfterSeconds = retryAfterSeconds;
  }
}

function getErrorMessage(status, data) {
  const detail = data?.detail;
  if (typeof detail === "string") return detail;
  if (detail && typeof detail === "object" && !Array.isArray(detail) && typeof detail.thong_bao === "string") {
    return detail.thong_bao;
  }
  if (Array.isArray(detail)) {
    const firstMessage = detail[0]?.msg;
    if (typeof firstMessage === "string" && firstMessage.startsWith("Value error, ")) {
      return firstMessage.slice("Value error, ".length);
    }
    return "Dữ liệu gửi lên không hợp lệ";
  }
  if (status === 401) return "Chưa đăng nhập hoặc phiên đã hết hạn";
  if (status === 403) return "Bạn không có quyền truy cập";
  if (status === 404) return "Không tìm thấy dữ liệu";
  if (status === 429) return "Bạn thao tác quá nhanh, vui lòng thử lại sau";
  if (status >= 500) return "Lỗi máy chủ, vui lòng thử lại";
  return `Yêu cầu thất bại (mã ${status})`;
}

function getRetryAfterSeconds(response) {
  const value = Number.parseInt(response.headers.get("Retry-After") ?? "", 10);
  return Number.isFinite(value) && value > 0 ? value : null;
}

async function parseBody(response) {
  if (response.status === 204) return null;
  const contentType = response.headers.get("Content-Type") || "";
  if (contentType.includes("application/json")) return response.json();
  const text = await response.text();
  return text || null;
}

export async function request(path, { method = "GET", body, token, signal } = {}) {
  const headers = { Accept: "application/json" };
  if (body !== undefined) headers["Content-Type"] = "application/json";
  if (token) headers.Authorization = `Bearer ${token}`;

  let response;
  try {
    response = await fetch(path, {
      method,
      headers,
      body: body !== undefined ? JSON.stringify(body) : undefined,
      signal,
    });
  } catch (error) {
    if (error.name === "AbortError") throw error;
    throw new HttpError(0, "Không kết nối được máy chủ");
  }

  const data = await parseBody(response);
  if (!response.ok) {
    throw new HttpError(
      response.status,
      getErrorMessage(response.status, data),
      data,
      getRetryAfterSeconds(response)
    );
  }
  return data;
}

export const http = {
  get: (path, options) => request(path, { ...options, method: "GET" }),
  post: (path, body, options) => request(path, { ...options, method: "POST", body }),
  put: (path, body, options) => request(path, { ...options, method: "PUT", body }),
  patch: (path, body, options) => request(path, { ...options, method: "PATCH", body }),
  delete: (path, options) => request(path, { ...options, method: "DELETE" }),
};