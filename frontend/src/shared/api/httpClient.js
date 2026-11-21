//là công cụ gọi API dùng chung. Các chức năng đăng nhập, đăng ký, lấy đề thi…
//  đều có thể dùng nó để gửi dữ liệu và nhận kết quả từ backend.


// lưu thông tin khi API báo lỗi
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
// chọn thông báo lỗi dễ hiểu 
// 401 chưa đăng nhập or hết hạn
// 403 không có quyền 
// 404 không tìm thấy 
//429 là thao tác quá nhanh
// 500 trở lên là lỗi máy chủ 
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
// đọc thời gian chờ
function getRetryAfterSeconds(response) {
  const value = Number.parseInt(response.headers.get("Retry-After") ?? "", 10);
  return Number.isFinite(value) && value > 0 ? value : null;
}
// đọc nội dung trả về từ backend, có thể là JSON hoặc text
// mã 204 là không có nội dung, trả về null
async function parseBody(response) {
  if (response.status === 204) return null;
  const contentType = response.headers.get("Content-Type") || "";
  if (contentType.includes("application/json")) return response.json();
  const text = await response.text();
  return text || null;
}
// thực hiện gọi API, trả về dữ liệu hoặc ném lỗi
// path là địa chỉ API
//method là phương thức get , post, pút, patch , delete
// body là dữ liệu cần gửi 
// token là mã xác thực đăng nhập
// signal cho phép hủy bỏ yêu cầu
// fetch là gửi yêu cầu đến backend, trả về phản hồi
//parseBody là đọc nội dung trả về từ backend, có thể là JSON hoặc text

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
// http.get lây dữ liệu từ backend
// http.post gửi dữ liệu đến backend
//put la thay đổi dữ liệu trên backend
//patch là sửa 1 phần
//delete là xóa dữ liệu trên backend
export const http = {
  get: (path, options) => request(path, { ...options, method: "GET" }),
  post: (path, body, options) => request(path, { ...options, method: "POST", body }),
  put: (path, body, options) => request(path, { ...options, method: "PUT", body }),
  patch: (path, body, options) => request(path, { ...options, method: "PATCH", body }),
  delete: (path, options) => request(path, { ...options, method: "DELETE" }),
};