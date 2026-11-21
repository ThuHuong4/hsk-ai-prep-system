import { http } from "../../../shared/api/httpClient.js";

export const getSurvey = (token, signal) => http.get("/api/khao-sat", { token, signal });
export const submitSurvey = (token, body) => http.post("/api/khao-sat", body, { token });
export const skipSurvey = (token) => http.post("/api/khao-sat/bo-qua", undefined, { token });
