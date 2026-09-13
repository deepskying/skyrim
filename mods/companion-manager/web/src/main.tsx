import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import "./previewRuntime";
import { GameApp } from "./GameApp";

import "./styles.css";

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <GameApp />
    {window.__companionPreview && (
      <div className="cm-preview-banner">
        界面预览 · 演示数据 · 游戏内以实际角色为准
      </div>
    )}
  </StrictMode>,
);
