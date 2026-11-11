import { useEffect, useState } from "react";

// loader(signal) trả Promise; loader = null thì bỏ qua (ví dụ tham số URL không hợp lệ)
export function useRequest(loader, deps) {
  const [state, setState] = useState({ data: null, error: "", loading: Boolean(loader) });

  useEffect(() => {
    if (!loader) {
      setState({ data: null, error: "", loading: false });
      return undefined;
    }
    const controller = new AbortController();
    setState({ data: null, error: "", loading: true });
    loader(controller.signal)
      .then((data) => setState({ data, error: "", loading: false }))
      .catch((err) => {
        if (err?.name === "AbortError") return;
        setState({ data: null, error: err?.message || "Không tải được dữ liệu", loading: false });
      });
    return () => controller.abort();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps);

  return state;
}