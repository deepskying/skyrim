import { useEffect, useState } from "react";
import type { GameFollower, InventoryItem, Snapshot } from "./bridge";
import { plainDescription, teachingBlock } from "./magic";

type Props = { snapshot: Snapshot | null; follower: GameFollower; busy: boolean; editable: boolean;
  command: (op: string, data: Record<string, unknown>) => boolean; onTeach: (book: InventoryItem) => void };
export function MagicPanel({ snapshot: s, follower: f, busy, editable, command, onTeach }: Props) {
  const [itemQuery, setItemQuery] = useState(""), [school, setSchool] = useState("全部");
  const inventory = s?.inventory ?? [];
  useEffect(() => { setItemQuery(""); setSchool("全部"); }, [f.id, s?.session]);
  return <>
    {(f.dead || f.unavailable) && <div className="info-box">人物目前不可操作，请稍后刷新。</div>}

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
            <div className={`cm-spell-cost ${spell.cost > f.magicka[1] ? "over" : ""}`}>
              <div><span>法力消耗 {spell.cost}</span><span>最大法力 {f.magicka[1]}</span></div>
              <progress aria-label={`${spell.name}法力消耗占比`} max={Math.max(1, f.magicka[1])} value={Math.min(spell.cost, Math.max(1, f.magicka[1]))} />
              {spell.cost > f.magicka[1] && <small>消耗超过最大法力</small>}
            </div>
            <p className="cm-description">
              {plainDescription(spell.description) ||
                "此法术未提供效果介绍。"}
            </p>
            <div className="cm-spell-control"><span>{spell.enabled ? "已启用" : "已禁用"}</span><button
              className={`switch ${spell.enabled ? "on" : ""}`}
              role="switch"
              aria-label={`${spell.name}使用`}
              aria-checked={spell.enabled}
              disabled={!editable}
              onClick={() =>
                command("spell", {
                  actorId: f.id,
                  entityId: spell.id,
                  value: !spell.enabled,
                })
              }
            >
              <span aria-hidden="true" />
            </button></div>
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
          const block = teachingBlock(s, f, b, busy),
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
                    onTeach(b)
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

  </>;
}
