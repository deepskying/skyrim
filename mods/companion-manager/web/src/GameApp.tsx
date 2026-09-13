import { useEffect, useRef, useState, type CSSProperties } from "react";
import { closeKey, percent, request, type Settings } from "./bridge";
import { useGame } from "./useGame";
import type { Section as DemoSection } from "./demo";
import "./game.css";
import { version } from "../package.json";
import { plainDescription, teachingBlock } from "./magic";
import { recruitmentCandidates, recruitmentBlock } from "./recruitment";

type Section = Exclude<DemoSection, "nearby">;
const sections: [Section, string, string][] = [
  ["party", "我的队伍", "♧"],
  ["registry", "随从名册", "▤"],
  ["settings", "全局设置", "⚙"],
];
type Tab = "概览" | "行为" | "魔法";
const tabs: Tab[] = ["概览", "行为", "魔法"];
type Confirmation = {
  title: string;
  description: string;
  command: string;
  data: Record<string, unknown>;
  quantity?: number;
};

function Toggle({
  label,
  description,
  value,
  disabled,
  onChange,
}: {
  label: string;
  description: string;
  value: boolean;
  disabled: boolean;
  onChange: () => void;
}) {
  return (
    <div className="setting-row">
      <div>
        <strong>{label}</strong>
        <p>{description}</p>
      </div>
      <button
        className={`switch ${value ? "on" : ""}`}
        role="switch"
        aria-label={label}
        aria-checked={value}
        disabled={disabled}
        onClick={onChange}
      >
        <span />
      </button>
    </div>
  );
}
function Resource({
  name,
  value,
  color,
}: {
  name: string;
  value: [number, number];
  color: string;
}) {
  return (
    <div className="cm-resource">
      <div>
        <span>{name}</span>
        <strong>
          {Math.round(value[0])} <small>/ {Math.round(value[1])}</small>
        </strong>
      </div>
      <div className="cm-track">
        <i style={{ width: `${percent(...value)}%`, background: color }} />
      </div>
    </div>
  );
}
export function GameApp() {
  const game = useGame(),
    s = game.snapshot;
  const [section, setSection] = useState<Section>("party"),
    [tab, setTab] = useState<Tab>("概览");
  const [selected, setSelected] = useState(""),
    [query, setQuery] = useState(""),
    [itemQuery, setItemQuery] = useState(""),
    [school, setSchool] = useState("全部");
  const [confirm, setConfirm] = useState<Confirmation | null>(null),
    [quantity, setQuantity] = useState(1);
  const [recruitOpen, setRecruitOpen] = useState(false),
    [recruitQuery, setRecruitQuery] = useState("");
  const candidates = recruitmentCandidates(s, recruitQuery);
  const modalRef = useRef<HTMLDivElement>(null);
  const rows =
    s?.followers.filter(
      (f) =>
        f.group === section &&
        `${f.name} ${f.race} ${f.id}`
          .toLowerCase()
          .includes(query.toLowerCase()),
    ) ?? [];
  const f = s?.followers.find((f) => f.id === selected && f.group === section);
  const enabled = !!s?.ready && !!s.managerAvailable && !game.busy;
  const editable = enabled && !!f?.managed && !f.dead && !f.unavailable;
  const prefs = s?.settings ?? {
    opacity: 82,
    font: 16,
    distance: 1,
    notifications: true,
    sandbox: true,
  };
  useEffect(() => {
    setConfirm(null);
    setRecruitOpen(false);
    setSelected("");
  }, [s?.session]);
  useEffect(() => {
    setItemQuery("");
    setSchool("全部");
  }, [f?.id, tab]);
  useEffect(() => {
    const close = (e: KeyboardEvent) => {
      if (
        closeKey(
          e,
          e.target instanceof HTMLElement &&
            (e.target.matches("input,textarea,select") ||
              e.target.isContentEditable),
        )
      ) {
        e.preventDefault();
        if (confirm) setConfirm(null);
        else if (recruitOpen) setRecruitOpen(false);
        else request("close");
      }
      if (e.key === "Tab" && (confirm || recruitOpen) && modalRef.current) {
        const focus = Array.from(
          modalRef.current.querySelectorAll<HTMLElement>(
            "button:not(:disabled),input:not(:disabled)",
          ),
        );
        if (focus.length) {
          const next = e.shiftKey ? focus[focus.length - 1] : focus[0];
          if (
            document.activeElement ===
            (e.shiftKey ? focus[0] : focus[focus.length - 1])
          ) {
            e.preventDefault();
            next.focus();
          }
        }
      }
    };
    window.addEventListener("keydown", close);
    return () => window.removeEventListener("keydown", close);
  }, [confirm, recruitOpen]);
  useEffect(() => {
    if (confirm || recruitOpen) {
      setQuantity(1);
      modalRef.current?.querySelector<HTMLElement>(recruitOpen ? "input" : "button")?.focus();
    }
  }, [confirm, recruitOpen]);
  const act = (command: string, data: Record<string, unknown> = {}) => {
    if (f) game.command(command, { ...data, actorId: f.id });
  };
  const ask = (
    title: string,
    description: string,
    command: string,
    data: Record<string, unknown> = {},
    max?: number,
  ) =>
    setConfirm({
      title,
      description,
      command,
      data: { ...data, actorId: f?.id },
      quantity: max,
    });
  const change = (key: keyof Settings, value: number | boolean) =>
    game.command("settings", { key, value });
  const toggle = (
    key: string,
    label: string,
    description: string,
    value: boolean,
    disabled = !editable,
  ) => (
    <Toggle
      key={key}
      label={label}
      description={description}
      value={value}
      disabled={disabled}
      onChange={() => act(key, { value: !value })}
    />
  );
  const style = {
    "--panel-alpha": prefs.opacity / 100,
    "--base-size": `${prefs.font}px`,
    "--text-scale": prefs.font / 15,
  } as CSSProperties;
  const inventory = s?.inventory ?? [];
  return (
    <div className="preview-world cm-runtime">
      <main className="app" style={style}>
        <aside className="sidebar">
          <div className="brand">
            <span className="brand-mark">∧</span>
            <div>
              同行<small>COMPANION MANAGER</small>
            </div>
          </div>
          <div className="nav-label">旅途与同伴</div>
          <nav>
            {sections.map(([id, label, icon]) => (
              <button
                key={id}
                className={section === id ? "selected" : ""}
                onClick={() => {
                  setSection(id);
                  setSelected("");
                  setTab("概览");
                  setQuery("");
                  setConfirm(null);
                }}
              >
                <span>{icon}</span>
                {label}
                {id !== "settings" && (
                  <small>
                    {s?.followers.filter((f) => f.group === id).length ?? 0}
                  </small>
                )}
              </button>
            ))}
          </nav>
          <div className="sidebar-bottom">
            <span className="location-dot" />
            {s?.location ?? "等待连接"}
            <small>Shift + F · 打开 / 关闭</small>
          </div>
        </aside>
        <section className="workspace">
          <header className="topbar">
            <div>
              <h1>{sections.find((x) => x[0] === section)?.[1]}</h1>
            </div>
            <div className="group-actions">
              {section === "party" && (
                <>
                  <button className="primary" disabled={!enabled}
                    onClick={() => {
                      setRecruitQuery("");
                      setRecruitOpen(true);
                      game.refresh();
                    }}>
                    招募同伴
                  </button>
                  <button
                    disabled={!enabled}
                    onClick={() => game.command("group", { action: "follow" })}
                  >
                    全队跟随
                  </button>
                  <button
                    disabled={!enabled}
                    onClick={() => game.command("group", { action: "wait" })}
                  >
                    全队等待
                  </button>
                  <button
                    disabled={!enabled}
                    onClick={() =>
                      setConfirm({
                        title: "召集整支队伍",
                        description:
                          "将本模组管理的在队同伴移动到你身边；剧情中的人物会被跳过。",
                        command: "group",
                        data: { action: "summon" },
                      })
                    }
                  >
                    集合
                  </button>
                </>
              )}
              <button
                aria-label="刷新游戏数据"
                disabled={game.busy}
                onClick={game.refresh}
              >
                ↻ 刷新
              </button>
              <button aria-label="关闭面板" onClick={() => request("close")}>
                ×
              </button>
            </div>
          </header>
          {section === "settings" ? (
            <div className="settings-page">
              <h2>按你的习惯同行</h2>
              <p>外观与行为偏好随当前游戏存档保存。</p>
              <div className="settings-grid">
                <div className="panel">
                  <h3>界面外观</h3>
                  <PreferenceRange
                    key={`opacity-${prefs.opacity}`}
                    label="面板不透明度"
                    value={prefs.opacity}
                    min={55}
                    max={96}
                    unit="%"
                    disabled={!enabled}
                    onSave={(v) => change("opacity", v)}
                  />
                  <PreferenceRange
                    key={`font-${prefs.font}`}
                    label="界面字号"
                    value={prefs.font}
                    min={14}
                    max={18}
                    unit="px"
                    disabled={!enabled}
                    onSave={(v) => change("font", v)}
                  />
                  <Toggle
                    label="操作成功提示"
                    description="失败和未确认的结果始终显示。"
                    value={prefs.notifications}
                    disabled={!enabled}
                    onChange={() =>
                      change("notifications", !prefs.notifications)
                    }
                  />
                </div>
                <div className="panel">
                  <h3>跟随偏好</h3>
                  <div className="setting-row">
                    <div>
                      <strong>跟随距离</strong>
                      <p>应用于本模组的所有在队同伴。</p>
                    </div>
                    <select
                      aria-label="跟随距离"
                      value={prefs.distance}
                      disabled={!enabled}
                      onChange={(e) => change("distance", +e.target.value)}
                    >
                      <option value={0}>近距离</option>
                      <option value={1}>适中</option>
                      <option value={2}>宽松</option>
                    </select>
                  </div>
                  <Toggle
                    label="新同伴自由活动"
                    description="新招募的人物在附近休息、使用家具。"
                    value={prefs.sandbox}
                    disabled={!enabled}
                    onChange={() => change("sandbox", !prefs.sandbox)}
                  />
                  <div className="info-box">
                    快捷键：Shift + F<br />
                    名册容量：64 位（包含离队同伴）
                    <br />
                    离队后可保留居所、法术与个人设置。
                  </div>
                </div>
              </div>
            </div>
          ) : (
            <div className="cm-content">
              {!f ? (
                <section className="cm-grid-page" aria-label="人物卡片网格">
                  <div className="cm-grid-heading">
                    <div>
                      <h2>
                        {section === "party"
                          ? "一起出发的伙伴"
                          : "暂别的旅伴"}
                      </h2>
                      <p>
                        {section === "party"
                          ? "通过对话招募后自动加入队伍；选择同伴即可安排行动或传授魔法。"
                          : "这里保留已离队同伴的记录，可以重新招募。"}
                      </p>
                    </div>
                    <input
                      className="cm-search"
                      aria-label="搜索人物"
                      placeholder="搜索姓名、种族…"
                      value={query}
                      onChange={(e) => setQuery(e.target.value)}
                    />
                  </div>
                  <div className="cm-follower-grid">
                    {rows.map((a) => (
                      <button
                        className="cm-follower-card"
                        key={a.id}
                        aria-label={`查看${a.name}详情`}
                        onClick={() => {
                          setSelected(a.id);
                          setTab("概览");
                        }}
                      >
                        <div className="cm-card-top">
                          <h3>{a.name}</h3>
                          <span className="cm-level">Lv. {a.level}</span>
                        </div>
                        <p className="cm-card-meta" title={`${a.race} · ${a.role} · 居所：${a.home}`}>
                          {a.race} · {a.role} · <span>{a.home === "未设置" ? "未设置居所" : a.home}</span>
                        </p>
                        <div className="cm-card-resources">
                          <Resource
                            name="生命"
                            value={a.health}
                            color="#9cd7b0"
                          />
                          <Resource
                            name="法力"
                            value={a.magicka}
                            color="#aabde9"
                          />
                          <Resource
                            name="耐力"
                            value={a.stamina}
                            color="#ddc389"
                          />
                        </div>
                        <div className="cm-card-bottom">
                          <span>
                            {a.dead
                              ? "已死亡"
                              : a.managed
                                ? a.group === "registry"
                                  ? "已离队"
                                  : a.waiting
                                    ? "原地等待"
                                    : "正在同行"
                                : a.canRecruit
                                  ? "待纳入管理"
                                  : "外部随从"}
                          </span>
                          <span>
                            {a.distance === null ? "异地" : `${a.distance} m`} ·
                            查看 →
                          </span>
                        </div>
                      </button>
                    ))}
                  </div>
                  {!rows.length && (
                    <div className="cm-welcome">
                      <h2>{s?.ready ? "这里暂时没有同伴" : "等待游戏数据"}</h2>
                      <p>
                        {query
                          ? "没有找到匹配的人物。"
                          : "当前没有可显示的同伴，可以刷新游戏数据。"}
                      </p>
                      <button disabled={game.busy} onClick={game.refresh}>
                        刷新
                      </button>
                    </div>
                  )}
                </section>
              ) : (
                <article className="detail cm-single-detail">
                  <div className="cm-detail-top">
                    <button onClick={() => setSelected("")}>
                      ← 返回{sections.find((x) => x[0] === section)?.[1]}
                    </button>
                    <div className="cm-person-title">
                      <h2>{f.name}</h2>
                      <span>
                        {f.race} · {f.role} · Lv. {f.level} · {f.location}
                      </span>
                    </div>
                    <div className="cm-header-home" aria-label="同伴居所">
                      <div className="cm-home-copy">
                        <span>当前居所</span>
                        <strong title={f.home}>{f.home}</strong>
                      </div>
                      <div className="cm-home-actions">
                        <button
                          disabled={!editable}
                          title="将你当前站立的位置设为这位同伴的居所"
                          onClick={() => ask(
                            "设置居所",
                            `将你当前站立的位置（${s?.location ?? "当前位置"}）设为${f.name}的居所。离队后，同伴会前往这里休息。`,
                            "home",
                            { clear: false },
                          )}
                        >
                          设置居所
                        </button>
                        {f.home !== "未设置" && (
                          <button
                            disabled={!editable}
                            onClick={() => ask(
                              "清除居所",
                              "清除这位同伴的居所，离队后恢复人物原有日程。",
                              "home",
                              { clear: true },
                            )}
                          >
                            清除
                          </button>
                        )}
                      </div>
                    </div>
                  </div>
                  <div className="tabs" role="tablist">
                    {tabs.map((t) => (
                      <button
                        key={t}
                        role="tab"
                        aria-selected={tab === t}
                        className={tab === t ? "active" : ""}
                        onClick={() => setTab(t)}
                      >
                        {t}
                      </button>
                    ))}
                  </div>
                  <div
                    className="detail-scroll"
                    role="tabpanel"
                    aria-label={tab}
                    key={`${f.id}-${tab}`}
                  >
                    {(f.dead || f.unavailable) && (
                      <div className="info-box">
                        {f.dead
                          ? "人物已死亡，可在行为页释放记录。"
                          : "人物正在参与剧情或暂不可操作，请稍后刷新。"}
                      </div>
                    )}
                    {!f.managed && !f.dead && (
                      <div className="info-box cm-enroll">
                        <div>
                          <strong>这位同伴尚未纳入同行管理</strong>
                          <p>{f.canRecruit
                            ? "纳入后即可安排其行动、设置居所和传授法术，无需先解散。"
                            : f.reason || "此人物目前不能纳入管理。"}</p>
                        </div>
                        <button className="primary"
                          disabled={!enabled || !f.canRecruit || f.unavailable}
                          onClick={() => ask(
                            "纳入同行管理",
                            `为${f.name}建立名册记录并启用同行的行动管理。已知法术保留，原有任务记录不清除；其他随从框架仍在运行时可能影响行动安排。`,
                            "adopt",
                          )}>
                          纳入同行管理
                        </button>
                      </div>
                    )}
                    {tab === "概览" && (
                      <>
                        <div className="cm-attribute-top">
                          <div className="cm-level-tile">
                            <span>角色等级</span>
                            <strong>{f.level}</strong>
                            <p>
                              {f.levelCap === null
                                ? "固定等级"
                                : `成长上限 ${f.levelCap === 0 ? "无限制" : f.levelCap}`}
                            </p>
                          </div>
                          <div className="cm-resource-panel">
                            <Resource
                              name="生命"
                              value={f.health}
                              color="#9cd7b0"
                            />
                            <Resource
                              name="法力"
                              value={f.magicka}
                              color="#aabde9"
                            />
                            <Resource
                              name="耐力"
                              value={f.stamina}
                              color="#ddc389"
                            />
                          </div>
                        </div>
                        {!!f.attributes?.length && (
                          <div className="panel">
                            <h3>基础属性</h3>
                            <div className="cm-stats">
                              {f.attributes.map((a) => (
                                <div key={a.name}>
                                  <span>{a.name}</span>
                                  <strong>{Number(a.value.toFixed(1))}</strong>
                                </div>
                              ))}
                            </div>
                          </div>
                        )}
                        <div className="cm-attribute-columns">
                          <div className="panel">
                            <h3>技能</h3>
                            <div className="cm-stats cm-skills">
                              {f.skills.map((a) => (
                                <div key={a.name}>
                                  <span>{a.name}</span>
                                  <strong>{Math.round(a.value)}</strong>
                                </div>
                              ))}
                            </div>
                          </div>
                          <div className="panel">
                            <h3>抗性</h3>
                            <div className="cm-stats">
                              {f.resistances.map((a) => (
                                <div key={a.name}>
                                  <span>{a.name}</span>
                                  <strong>{Math.round(a.value)}%</strong>
                                </div>
                              ))}
                            </div>
                            <p>
                              当前状态：{f.inCombat ? "正在交战" : "未在战斗中"}
                            </p>
                            {toggle(
                              "levelCap",
                              "提高成长上限",
                              f.canRaise
                                ? `入队自动开启，上限至少 300；关闭恢复 ${f.originalMax}。`
                                : "固定等级或原本无上限，无需覆盖。",
                              f.raised,
                              !editable || !f.canRaise,
                            )}
                          </div>
                        </div>
                      </>
                    )}
                    {tab === "行为" && (
                      <>
                        <div className="cm-behavior-columns">
                          <div className="panel">
                            <h3>行动安排</h3>
                            {toggle(
                              "wait",
                              "原地等待",
                              "结束等待后恢复跟随。",
                              f.waiting,
                              !editable || f.group !== "party",
                            )}
                            {toggle(
                              "sandbox",
                              "自由活动",
                              "停留时可以休息与使用附近设施。",
                              f.sandbox,
                            )}
                            {toggle(
                              "leash",
                              "自动跟上",
                              "落后或跨区域时返回，等待及交战时不传送。",
                              f.leash,
                            )}
                            {toggle(
                              "passive",
                              "避免交战",
                              "降低攻击性与战斗信心，尝试停止战斗。",
                              f.passive,
                            )}
                            {toggle(
                              "protection",
                              "死亡保护",
                              "启用 Essential 保护。",
                              f.essential,
                            )}
                          </div>
                          <div className="panel">
                            <div className="cm-person-actions">
                              <h3>队伍管理</h3>
                              <div className="button-row">
                                <button
                                  disabled={!editable}
                                  onClick={() =>
                                    ask(
                                      "召回同伴",
                                      `将${f.name}移动到你身边。`,
                                      "summon",
                                    )
                                  }
                                >
                                  召回身边
                                </button>
                                {f.managed && f.group === "party" && !f.dead ? (
                                  <button
                                    disabled={!editable}
                                    onClick={() =>
                                      ask(
                                        "让同伴离队",
                                        "离队后保留在随从名册，已有居所与个人设置会保留。",
                                        "dismiss",
                                      )
                                    }
                                  >
                                    解散
                                  </button>
                                ) : (
                                  <button
                                    className="primary"
                                    disabled={
                                      !enabled ||
                                      f.dead ||
                                      f.unavailable ||
                                      (!f.managed && !f.canRecruit)
                                    }
                                    onClick={() =>
                                      ask(
                                        f.managed ? "邀请加入队伍" : "纳入同行管理",
                                        `由同行管理${f.name}的行动、居所与法术。`,
                                        f.managed ? "recruit" : "adopt",
                                      )
                                    }
                                  >
                                    {f.managed ? "重新入队" : "纳入同行管理"}
                                  </button>
                                )}
                                {f.managed &&
                                  (f.group === "registry" || f.dead) && (
                                    <button
                                      disabled={!enabled}
                                      onClick={() =>
                                        ask(
                                          "释放名册记录",
                                          "解除管理，恢复原始行为、保护和等级上限。已学习法术保留，被禁用法术恢复。",
                                          "forget",
                                        )
                                      }
                                    >
                                      释放名册
                                    </button>
                                  )}
                              </div>
                            </div>
                          </div>
                        </div>
                      </>
                    )}
                    {tab === "魔法" && (
                      <>
                        <div className="cm-magic-tools">
                          <input
                            className="cm-search"
                            aria-label="搜索法术"
                            placeholder="搜索法术或法术书…"
                            value={itemQuery}
                            onChange={(e) => setItemQuery(e.target.value)}
                          />
                          <select
                            aria-label="法术学派"
                            value={school}
                            onChange={(e) => setSchool(e.target.value)}
                          >
                            {[
                              "全部",
                              ...new Set([
                                ...f.spells.map((x) => x.school),
                                ...inventory
                                  .filter((x) => x.spellId && x.school)
                                  .map((x) => x.school!),
                              ]),
                            ].map((x) => (
                              <option key={x}>{x}</option>
                            ))}
                          </select>
                        </div>
                        <div className="section-title">
                          <h3>
                            已知法术 <small>{f.spells.length}</small>
                          </h3>
                          <p>管理这位同伴可以使用的法术</p>
                        </div>
                        <div className="cm-magic-grid">
                          {f.spells
                            .filter(
                              (x) =>
                                (school === "全部" || x.school === school) &&
                                x.name.includes(itemQuery),
                            )
                            .map((spell) => (
                              <div
                                className={`cm-magic-card ${spell.enabled ? "" : "disabled"}`}
                                key={spell.id}
                              >
                                <div className="cm-magic-card-head">
                                  <span className="cm-spell-mark">✧</span>
                                  <div>
                                    <h3>{spell.name}</h3>
                                    <p>
                                      {spell.school} · {spell.cost} 法力
                                    </p>
                                  </div>
                                </div>
                                <p className="cm-description">
                                  {plainDescription(spell.description) ||
                                    "此法术未提供效果介绍。"}
                                </p>
                                <button
                                  role="switch"
                                  aria-label={`${spell.name}使用`}
                                  aria-checked={spell.enabled}
                                  disabled={!editable}
                                  onClick={() =>
                                    act("spell", {
                                      entityId: spell.id,
                                      value: !spell.enabled,
                                    })
                                  }
                                >
                                  {spell.enabled
                                    ? "已启用 · 点击禁用"
                                    : "已禁用 · 点击恢复"}
                                </button>
                              </div>
                            ))}
                        </div>
                        {!f.spells.length && (
                          <p className="cm-empty">此角色尚未掌握普通法术。</p>
                        )}
                        <div className="cm-tome-heading">
                          <span className="eyebrow">将知识交给旅伴</span>
                          <h3>从背包传授法术</h3>
                          <p>阅读法术介绍后传授；成功学习消耗一本法术书。</p>
                        </div>
                        {!s?.managerAvailable && (
                          <div className="cm-notice failure" role="alert">
                            教学不可用：请在 MO2 右侧启用
                            CompanionManager.esp，重新启动游戏。
                          </div>
                        )}
                        {s?.managerAvailable && !f.managed && (
                          <div className="info-box">
                            此人物尚未由同行管理，暂不支持修改其法术；不会直接接管其他模组的随从。
                          </div>
                        )}
                        <div className="cm-magic-grid cm-tome-grid">
                          {inventory
                            .filter(
                              (b) =>
                                b.spellId &&
                                (school === "全部" ||
                                  !b.school ||
                                  b.school === school) &&
                                `${b.name}${b.spellName}`.includes(itemQuery),
                            )
                            .map((b) => {
                              const block = teachingBlock(s, f, b, game.busy),
                                known = f.spells.some(
                                  (x) => x.id === b.spellId,
                                );
                              const intro =
                                plainDescription(b.spellDescription) ||
                                plainDescription(b.description);
                              return (
                                <article
                                  className="cm-magic-card cm-tome"
                                  key={b.id}
                                >
                                  <div className="cm-magic-card-head">
                                    <span className="cm-spell-mark">▥</span>
                                    <div>
                                      <h3>{b.spellName}</h3>
                                      <p>
                                        {b.school ?? "法术书"}
                                        {b.cost !== undefined
                                          ? ` · ${b.cost} 法力（玩家）`
                                          : ""}
                                      </p>
                                    </div>
                                    <span className="cm-book-count">
                                      ×{b.count}
                                    </span>
                                  </div>
                                  <p className="cm-description">
                                    {intro || "这本法术书未提供介绍。"}
                                  </p>
                                  {plainDescription(b.description) &&
                                    plainDescription(b.description) !==
                                      intro && (
                                      <details>
                                        <summary>书本正文</summary>
                                        <p className="cm-description">
                                          {plainDescription(b.description)}
                                        </p>
                                      </details>
                                    )}
                                  <div className="cm-tome-foot">
                                    <small>{b.name}</small>
                                    <button
                                      className="primary"
                                      disabled={!!block}
                                      aria-describedby={`book-${b.id}`}
                                      onClick={() =>
                                        ask(
                                          "传授法术",
                                          `消耗一本${b.name}，让${f.name}学会${b.spellName}。`,
                                          "teach",
                                          { entityId: b.id },
                                        )
                                      }
                                    >
                                      {known
                                        ? "已掌握"
                                        : b.quest
                                          ? "任务物品"
                                          : "传授法术"}
                                    </button>
                                  </div>
                                  {block && (
                                    <p
                                      className="cm-block-reason"
                                      id={`book-${b.id}`}
                                    >
                                      {block}
                                    </p>
                                  )}
                                </article>
                              );
                            })}
                        </div>
                        {!inventory.some((b) => b.spellId) && (
                          <p className="cm-empty">
                            背包中没有法术书。获得法术书后，点击右上角刷新。
                          </p>
                        )}
                      </>
                    )}
                  </div>
                </article>
              )}
            </div>
          )}
          <footer className="cm-statusbar" aria-label="面板状态栏">
          {game.notice && (!game.notice.ok || prefs.notifications) && (
            <div
              className={`cm-notice ${game.notice.ok ? "success" : "failure"}`}
              role={game.notice.ok ? "status" : "alert"}
            >
              {game.notice.message}
            </div>
          )}
          {s?.truncated && (
            <div className="cm-notice">
              人物较多，当前最多显示 128 位；已登记同伴优先。
            </div>
          )}
            <div className="cm-status-row">
              <span className="cm-status-message" role="status">
                {game.busy ? "正在处理，请稍候…" : game.status}
              </span>
              <span className="cm-status-meta">
                {game.updated && `${game.updated} 更新 · `}游戏继续运行
              </span>
              <span className="cm-status-version">同行 v{version}</span>
            </div>
          </footer>
        </section>
        {recruitOpen && (
          <div className="modal-scrim">
            <div className="modal cm-recruit-dialog" ref={modalRef} role="dialog"
              aria-modal="true" aria-labelledby="cm-recruit-title">
              <div className="cm-recruit-heading">
                <h2 id="cm-recruit-title">招募同伴</h2>
                <button aria-label="关闭招募窗口" onClick={() => setRecruitOpen(false)}>×</button>
              </div>
              <p>对话招募的同伴会自动登记。这里也可直接招募附近人物，或手动纳入其他队友。名册已用 {s?.followers.filter(a => a.managed).length ?? 0} / 64 位。</p>
              <div className="cm-recruit-tools">
                <input aria-label="搜索招募人物" placeholder="搜索姓名、种族…"
                  value={recruitQuery} onChange={e => setRecruitQuery(e.target.value)} />
                <button disabled={game.busy} onClick={game.refresh}>刷新列表</button>
              </div>
              <div className="cm-recruit-list">
                {candidates.map(actor => {
                  const block = recruitmentBlock(s, actor, game.busy);
                  return <div className="cm-recruit-row" key={actor.id}>
                    <div>
                      <strong>{actor.name}</strong>
                      <span>{actor.race} · Lv. {actor.level} · {actor.distance === null ? "异地" : `${actor.distance} m`}</span>
                      {block && <small>{block}</small>}
                    </div>
                    <button disabled={!!block} aria-label={`${actor.group === "party" ? "纳入" : "招募"}${actor.name}`}
                      onClick={() => {
                        setRecruitOpen(false);
                        setConfirm({
                          title: actor.group === "party" ? "纳入同行管理" : "招募同伴",
                          description: `让${actor.name}加入同行的队伍，管理其行动、居所与法术。`,
                          command: actor.group === "party" ? "adopt" : "recruit",
                          data: { actorId: actor.id },
                        });
                      }}>
                      {actor.group === "party" ? "纳入管理" : "招募入队"}
                    </button>
                  </div>;
                })}
                {!candidates.length && <p className="cm-empty">{recruitQuery ? "没有匹配的人物。" : "附近没有可显示的人物，请靠近目标后刷新列表。"}</p>}
              </div>
            </div>
          </div>
        )}
        {confirm && (
          <div className="modal-scrim">
            <div
              ref={modalRef}
              className="modal"
              role="dialog"
              aria-modal="true"
              aria-labelledby="cm-modal-title"
            >
              <span className="eyebrow">确认操作</span>
              <h2 id="cm-modal-title">{confirm.title}</h2>
              <p>{confirm.description}</p>
              {confirm.quantity !== undefined && (
                <label className="cm-quantity">
                  数量{" "}
                  <input
                    aria-label="转移数量"
                    type="number"
                    min={1}
                    max={confirm.quantity}
                    value={quantity}
                    onChange={(e) => setQuantity(Number(e.target.value))}
                  />
                  <small>最多 {confirm.quantity}</small>
                </label>
              )}
              <div className="button-row">
                <button onClick={() => setConfirm(null)}>取消</button>
                <button
                  className="primary"
                  disabled={
                    !enabled ||
                    !Number.isInteger(quantity) ||
                    quantity < 1 ||
                    (confirm.quantity !== undefined &&
                      quantity > confirm.quantity)
                  }
                  onClick={() => {
                    const c = confirm;
                    if (
                      game.command(c.command, {
                        ...c.data,
                        ...(c.quantity !== undefined
                          ? { count: quantity }
                          : {}),
                      })
                    )
                      setConfirm(null);
                  }}
                >
                  确认
                </button>
              </div>
            </div>
          </div>
        )}
      </main>
    </div>
  );
}

function PreferenceRange({
  label,
  value,
  min,
  max,
  unit,
  disabled,
  onSave,
}: {
  label: string;
  value: number;
  min: number;
  max: number;
  unit: string;
  disabled: boolean;
  onSave: (value: number) => void;
}) {
  const [draft, setDraft] = useState(value);
  return (
    <div className="cm-preference">
      <label>
        {label}
        <strong>
          {draft}
          {unit}
        </strong>
        <input
          aria-label={label}
          type="range"
          min={min}
          max={max}
          value={draft}
          disabled={disabled}
          onChange={(e) => setDraft(+e.target.value)}
        />
      </label>
      <button
        disabled={disabled || draft === value}
        onClick={() => onSave(draft)}
      >
        应用
      </button>
    </div>
  );
}
