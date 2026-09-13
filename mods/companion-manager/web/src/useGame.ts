import { useEffect, useRef, useState } from "react";
import {
  isGameLocation,
  parseSnapshot,
  request,
  send,
  type Snapshot,
} from "./bridge";

export const gameMode =
  !!window.__companionPreview ||
  isGameLocation(window.location.protocol, window.location.search);
document.documentElement.dataset.runtime =
  gameMode && !window.__companionPreview ? "game" : "demo";

export function useGame() {
  const [snapshot, setSnapshot] = useState<Snapshot | null>(null);
  const current = useRef<Snapshot | null>(null);
  const [status, setStatus] = useState("等待游戏连接…");
  const [busy, setBusy] = useState(false);
  const [updated, setUpdated] = useState("");
  const [notice, setNotice] = useState<{ ok: boolean; message: string } | null>(
    null,
  );
  const pending = useRef("");
  const timer = useRef<ReturnType<typeof setTimeout> | undefined>(undefined);
  const sequence = useRef(0);
  const prefix = useRef(
    `${Date.now()}-${Math.random().toString(36).slice(2, 9)}`,
  );
  const clear = () => {
    clearTimeout(timer.current);
    pending.current = "";
    setBusy(false);
  };
  const wait = (id: string) => {
    pending.current = id;
    setBusy(true);
    clearTimeout(timer.current);
    timer.current = setTimeout(() => {
      clear();
      current.current = null;
      setSnapshot(null);
      setStatus("响应超时，结果尚未确认。请刷新检查实际状态后再操作。");
    }, 15000);
  };
  useEffect(() => {
    if (!gameMode) return;
    const receive = () => {
      const next = parseSnapshot(window.__companionSnapshot);
      if (!next) {
        clear();
        current.current = null;
        setSnapshot(null);
        setStatus("游戏数据格式不匹配，请更新完整安装包。");
        return;
      }
      if (current.current?.session !== next.session) {
        clear();
        setNotice(null);
      }
      if (pending.current === "refresh") clear();
      current.current = next;
      setSnapshot(next);
      setStatus(
        !next.ready
          ? "请先载入存档进入游戏"
          : !next.managerAvailable
            ? "CompanionManager.esp 未加载，请在 MO2 右侧启用"
            : window.__companionPreview ? "设计预览 · 演示数据" : "已连接游戏 · 实时管理",
      );
      setUpdated(new Date().toLocaleTimeString("zh-CN", { hour12: false }));
    };
    const reset = () => {
      clear();
      current.current = null;
      setSnapshot(null);
      setNotice(null);
      setUpdated("");
      setStatus("存档已切换，等待重新读取");
    };
    const error = () => {
      clear();
      current.current = null;
      setSnapshot(null);
      setStatus("读取失败，请重试或查看 CompanionManager.log");
    };
    const result = (event: Event) => {
      const detail = (event as CustomEvent).detail;
      if (
        !detail ||
        typeof detail !== "object" ||
        detail.requestId !== pending.current ||
        typeof detail.ok !== "boolean" ||
        typeof detail.message !== "string"
      )
        return;
      clear();
      setNotice({ ok: detail.ok, message: detail.message });
    };
    window.addEventListener("companion:snapshot", receive);
    window.addEventListener("companion:reset", reset);
    window.addEventListener("companion:error", error);
    window.addEventListener("companion:result", result);
    if (window.__companionSnapshot !== undefined) receive();
    if (!current.current) wait("refresh");
    request("refresh");
    return () => {
      clearTimeout(timer.current);
      window.removeEventListener("companion:snapshot", receive);
      window.removeEventListener("companion:reset", reset);
      window.removeEventListener("companion:error", error);
      window.removeEventListener("companion:result", result);
    };
  }, []);
  const refresh = () => {
    if (pending.current) return;
    wait("refresh");
    if (!request("refresh")) {
      clear();
      setStatus("游戏接口不可用，请检查 Meridian 和原生插件");
    }
  };
  const command = (command: string, data: Record<string, unknown> = {}) => {
    const s = current.current;
    if (pending.current || !s?.ready || !s.managerAvailable) return false;
    const requestId = `${prefix.current}-${++sequence.current}`;
    wait(requestId);
    setNotice(null);
    if (
      !send({
        ...data,
        type: "command",
        command,
        session: s.session,
        requestId,
      })
    ) {
      clear();
      setNotice({ ok: false, message: "指令未发送，游戏接口不可用" });
      return false;
    }
    return true;
  };
  return { snapshot, status, busy, updated, refresh, command, notice };
}
