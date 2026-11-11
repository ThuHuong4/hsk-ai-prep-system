import { http } from "../../../shared/api/httpClient.js";

export function getHskLevels(signal) {
  return http.get("/api/hsk-levels", { signal });
}