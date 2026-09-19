import { useEffect, useId, useRef, useState } from "react";
import type { GameFollower } from "./bridge";

type Props = { followers: GameFollower[]; value: string; label?: string; onChange: (id: string) => void };

export function CompanionPicker({ followers, value, onChange, label = "查看伙伴库存" }: Props) {
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState("");
  const [active, setActive] = useState(0);
  const root = useRef<HTMLDivElement>(null);
  const trigger = useRef<HTMLButtonElement>(null);
  const search = useRef<HTMLInputElement>(null);
  const listId = useId();
  const current = followers.find(f => f.id === value);
  const matches = followers.filter(f => f.name.toLocaleLowerCase().includes(query.trim().toLocaleLowerCase()));
  const index = Math.min(active, matches.length - 1);
  const status = (f: GameFollower) => f.group === "registry" ? "已离队" : "在队";
  const close = (restoreFocus = false) => {
    setOpen(false);
    if (restoreFocus) trigger.current?.focus();
  };
  const show = () => {
    setQuery("");
    setActive(Math.max(0, followers.findIndex(f => f.id === value)));
    setOpen(true);
  };
  const choose = (id: string) => { onChange(id); close(true); };

  useEffect(() => {
    if (!open) return;
    search.current?.focus();
    const outside = (event: PointerEvent) => {
      if (!root.current?.contains(event.target as Node)) setOpen(false);
    };
    document.addEventListener("pointerdown", outside);
    return () => document.removeEventListener("pointerdown", outside);
  }, [open]);
  useEffect(() => {
    if (open && index >= 0) document.getElementById(`${listId}-${index}`)?.scrollIntoView({ block: "nearest" });
  }, [open, index, listId, query]);
  useEffect(() => { setOpen(false); }, [value]);

  return <div className="cm-companion-picker" ref={root}
    onBlur={event => { if (!event.currentTarget.contains(event.relatedTarget as Node | null)) close(); }}
    onKeyDown={event => {
      if (open && event.key === "Escape") { event.preventDefault(); event.stopPropagation(); close(true); }
    }}>
    <button type="button" className="cm-companion-trigger" ref={trigger}
      aria-label={`选择管理伙伴：${current?.name ?? "暂无伙伴"}`} aria-haspopup="listbox" aria-expanded={open}
      aria-controls={open ? listId : undefined} disabled={!followers.length}
      onClick={() => open ? close() : show()}
      onKeyDown={event => { if (event.key === "ArrowDown" || event.key === "ArrowUp") { event.preventDefault(); show(); } }}>
      <span className="cm-companion-avatar" aria-hidden="true">{current?.name.slice(0, 1) ?? "◇"}</span>
      <span className="cm-companion-current"><small>{label}</small><strong title={current?.name}>{current?.name ?? "暂无伙伴"}</strong></span>
      {current && <span className={`cm-companion-status ${current.group === "registry" ? "away" : ""}`}>{status(current)}</span>}
      <span className="cm-companion-chevron" aria-hidden="true">{open ? "▴" : "▾"}</span>
    </button>
    {open && <div className="cm-companion-popover">
      <input ref={search} role="combobox" aria-label="搜索伙伴姓名" placeholder="搜索伙伴姓名…"
        aria-expanded={true} aria-controls={listId} aria-autocomplete="list"
        aria-activedescendant={index >= 0 ? `${listId}-${index}` : undefined}
        value={query} onChange={event => { setQuery(event.target.value); setActive(0); }}
        onKeyDown={event => {
          if (event.nativeEvent.isComposing) return;
          if (event.key === "ArrowDown" || event.key === "ArrowUp") {
            event.preventDefault();
            setActive(matches.length ? (index + (event.key === "ArrowDown" ? 1 : -1) + matches.length) % matches.length : 0);
          } else if (event.key === "Enter") {
            event.preventDefault();
            if (matches[index]) choose(matches[index].id);
          }
        }} />
      <div className="cm-companion-list" role="listbox" aria-label="伙伴" id={listId}>
        {matches.map((f, i) => <div role="option" id={`${listId}-${i}`} key={f.id}
          aria-selected={f.id === value} className={`cm-companion-option ${i === index ? "active" : ""}`}
          onPointerMove={() => setActive(i)} onMouseDown={event => event.preventDefault()} onClick={() => choose(f.id)}>
          <span className="cm-companion-name">{f.name}</span>
          <span className={`cm-companion-status ${f.group === "registry" ? "away" : ""}`}>{status(f)}</span>
          <span className="cm-companion-check" aria-hidden="true">{f.id === value ? "✓" : ""}</span>
        </div>)}
      </div>
      {!matches.length && <p className="cm-companion-empty" role="status">没有找到匹配的伙伴</p>}
      <div className="cm-companion-count">{query.trim() ? `找到 ${matches.length} 位伙伴` : `共 ${followers.length} 位伙伴`}</div>
    </div>}
  </div>;
}
