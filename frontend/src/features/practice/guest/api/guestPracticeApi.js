import { http } from "../../../../shared/api/httpClient.js";

// API công khai: không gửi token, máy chủ không lưu gì
export const getGuestOverview = (signal) => http.get("/api/cong-khai/on-luyen/tong-quan", { signal });
export const getGuestPath = (kyNang, capDoId, signal) =>
  http.get(`/api/cong-khai/on-luyen/lo-trinh?ky_nang=${kyNang}${capDoId ? `&cap_do_id=${capDoId}` : ""}`, { signal });
export const getGuestLesson = (maGoc, signal) => http.get(`/api/cong-khai/on-luyen/bai/${maGoc}`, { signal });
export const checkGuestAnswer = (maGoc, body) => http.post(`/api/cong-khai/on-luyen/bai/${maGoc}/kiem-tra`, body);
export const askGuestXiang = (body) => http.post("/api/cong-khai/hoi-xiang", body);
