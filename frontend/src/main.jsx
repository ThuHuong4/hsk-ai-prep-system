import { StrictMode } from "react";

import { createRoot } from "react-dom/client";
import "./styles/tokens.css";
import "./styles/global.css";
import App from "./app/App.jsx";
import { applyTheme, readTheme } from "./shared/hooks/useTheme.js";

applyTheme(readTheme());

createRoot(document.getElementById("root")).render(
  <StrictMode>
    <App />
  </StrictMode>
);