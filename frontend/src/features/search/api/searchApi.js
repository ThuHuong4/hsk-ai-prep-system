import { http } from "../../../shared/api/httpClient.js";

// Công khai: từ vựng đã xuất bản + đề thi thử đã đăng (mục 3.2)
export const searchAll = (q, signal) => http.get(`/api/tim-kiem?q=${encodeURIComponent(q)}`, { signal });
