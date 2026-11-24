import { useEffect, useState } from "react";

import { useAuth } from "../../auth/context/AuthContext.jsx";
import { listKnowledgeGroups } from "../api/lecturerApi.js";

// Danh mục nhóm kiến thức đang hoạt động: [{ id, ma, ten }]
export function useKnowledgeGroups() {
  const { token } = useAuth();
  const [groups, setGroups] = useState([]);
  useEffect(() => {
    const controller = new AbortController();
    listKnowledgeGroups(token, controller.signal)
      .then((data) => setGroups(data.items || []))
      .catch(() => setGroups([]));
    return () => controller.abort();
  }, [token]);
  return groups;
}
