import { http } from "../../../shared/api/httpClient.js";

export const getMyStats = (token, signal) => http.get("/api/thi-thu/thong-ke", { token, signal });
