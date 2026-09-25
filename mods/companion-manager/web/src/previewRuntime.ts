import { fixture, simulate } from "./preview-data.mjs";

// HTTP design preview uses exactly the same cards and detail pages as the game.
if (
  location.protocol !== "mod:" &&
  new URLSearchParams(location.search).get("runtime") !== "game"
) {
  window.__companionPreview = true;
  const state = fixture();
  state.location = "雪漫领 · 设计预览";
  state.followers[0].location = "雪漫城";
  const first = state.followers[0];
  state.followers.push(
    {
      ...structuredClone(first),
      id: "00000011",
      name: "伊奥拉",
      race: "布莱顿人",
      role: "法师",
      mark: "法",
      tint: "purple",
      level: 28,
      health: [180, 180],
      magicka: [240, 280],
      stamina: [150, 150],
    },
    {
      ...structuredClone(first),
      id: "00000012",
      name: "法恩达尔",
      race: "木精灵",
      role: "游侠",
      mark: "弓",
      level: 25,
      waiting: true,
      health: [205, 230],
      magicka: [80, 80],
      stamina: [230, 250],
    },
    {
      ...structuredClone(first),
      id: "00000013",
      name: "乌斯盖德",
      managed: false,
      raised: false,
      levelCap: 50,
      canRaise: false,
      limited: true,
      canRecruit: true,
      role: "战士",
      mark: "剑",
      level: 32,
      health: [310, 310],
      stamina: [190, 220],
    },
  );
  const snapshot = () => {
    window.__companionSnapshot = structuredClone(state);
    window.dispatchEvent(new Event("companion:snapshot"));
  };
  window.companionRequest = (payload) => {
    const r = JSON.parse(payload);
    if (r.type === "refresh") snapshot();
    // The HTTP preview has no renderer, so it answers the wear page's status poll with whatever the
    // page is being reviewed against; without the override it reports an unconnected renderer.
    if (typeof r.type === "string" && r.type.startsWith("preview")) {
      if (r.type === "previewStatus")
        window.dispatchEvent(
          new CustomEvent("companion:preview-status", {
            detail: { id: r.id, token: r.token, status: window.__companionPreviewStatus ?? "unavailable" },
          }),
        );
      return;
    }
    if (r.type === "command")
      setTimeout(() => {
        const result = simulate(state, r);
        window.dispatchEvent(
          new CustomEvent("companion:result", {
            detail: { ...result, requestId: r.requestId },
          }),
        );
        snapshot();
      }, 180);
    if (r.type === "close")
      window.dispatchEvent(
        new CustomEvent("companion:result", {
          detail: { message: "游戏内可使用 Shift + F 关闭" },
        }),
      );
  };
  snapshot();
}
