import { http } from "../../../shared/api/httpClient.js";

// Học viên báo lỗi nội dung câu hỏi và xem phản hồi của Giảng viên
export const sendReport = (token, body) => http.post("/api/bao-loi", body, { token });
export const listMyReports = (token, signal) => http.get("/api/bao-loi/cua-toi", { token, signal });
