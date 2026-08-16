import { useEffect, useMemo, useState } from 'react';
import './styles.css';

type Spell = {
  id: string;
  name: string;
  school: string;
  cost: number;
};

type Resource = {
  current: number;
  max: number;
};

type LevelScaling = {
  playerScaled: boolean;
  multiplier: number;
  currentMax: number;
  originalMax: number;
  targetMax: number;
  enabled: boolean;
  canToggle: boolean;
};

type Follower = {
  id: string;
  name: string;
  className: string;
  level: number;
  levelScaling: LevelScaling;
  maxMagicka: number;
  resources: {
    health: Resource;
    magicka: Resource;
    stamina: Resource;
  };
  spells: Spell[];
};

type Tome = Spell & {
  spellName: string;
  count: number;
  value: number;
  description: string;
};

type State = {
  followers: Follower[];
  tomes: Tome[];
  message?: string;
};

type NativeBridge = {
  receiveState?: (next: State) => void;
};

declare global {
  interface Window {
    FollowerSpellbook?: NativeBridge;
    followerSpellbookAction?: (data: string) => void;
  }
}

const demo: State = {
  followers: [
    { id: 'demo-lydia', name: 'Lydia', className: 'Combat Warrior', level: 34, levelScaling: { playerScaled: true, multiplier: 1, currentMax: 50, originalMax: 50, targetMax: 300, enabled: false, canToggle: true }, maxMagicka: 100, resources: { health: { current: 312, max: 360 }, magicka: { current: 72, max: 100 }, stamina: { current: 185, max: 240 } }, spells: [{ id: 'ice-spike', name: 'Ice Spike', school: 'Destruction', cost: 30 }] },
    { id: 'demo-serana', name: 'Serana', className: 'Vampire Mystic', level: 48, levelScaling: { playerScaled: true, multiplier: 1, currentMax: 300, originalMax: 50, targetMax: 300, enabled: true, canToggle: true }, maxMagicka: 220, resources: { health: { current: 280, max: 280 }, magicka: { current: 146, max: 220 }, stamina: { current: 124, max: 170 } }, spells: [{ id: 'firebolt', name: 'Firebolt', school: 'Destruction', cost: 25 }] },
  ],
  tomes: [
    { id: 'firebolt-tome', name: 'Spell Tome: Firebolt', spellName: 'Firebolt', school: 'Destruction', cost: 25, count: 1, value: 96, description: 'A blast of fire that does 25 points of damage.' },
    { id: 'fast-healing-tome', name: 'Spell Tome: Fast Healing', spellName: 'Fast Healing', school: 'Restoration', cost: 73, count: 2, value: 149, description: 'Heals the caster 50 points.' },
  ],
  message: 'Choose a follower and a spell tome to begin.',
};

const empty: State = { followers: [], tomes: [], message: 'Loading follower data…' };
const initialState = import.meta.env.DEV ? demo : empty;

function send(type: string, data: Record<string, unknown> = {}) {
  if (typeof window.followerSpellbookAction !== 'function') return;
  window.followerSpellbookAction(JSON.stringify({ type, ...data }));
}

function SchoolPill({ school }: { school: string }) {
  return <span className="school">{school || 'Other'}</span>;
}

function ResourceBar({ label, resource, kind }: { label: string; resource: Resource; kind: 'health' | 'magicka' | 'stamina' }) {
  const ratio = resource.max > 0 ? Math.min(100, Math.max(0, (resource.current / resource.max) * 100)) : 0;
  return (
    <span className="resource-row">
      <span className="resource-caption"><span>{label}</span><small>{resource.current} / {resource.max}</small></span>
      <span className="resource-track"><span className={kind} style={{ width: `${ratio}%` }} /></span>
    </span>
  );
}

function FollowerCard({ follower, onOpen }: { follower: Follower; onOpen: () => void }) {
  const scaling = follower.levelScaling;
  const scalingText = !scaling.playerScaled
    ? 'Fixed level'
    : scaling.enabled
      ? `Cap raised · ${scaling.currentMax}`
      : scaling.currentMax === 0
        ? `Player ×${scaling.multiplier.toFixed(2)} · no cap`
        : `Player ×${scaling.multiplier.toFixed(2)} · cap ${scaling.currentMax}`;
  return (
    <button className="follower-card" onClick={onOpen} type="button">
      <span className="follower-card-heading">
        <span className="card-sigil">✦</span>
        <span className="follower-card-copy">
          <strong>{follower.name}</strong>
          <small>{follower.className || 'Unclassified'} · {follower.spells.length} known spells</small>
        </span>
        <span className="level-badge">Lv.{follower.level}</span>
      </span>
      <span className={`scaling-badge ${scaling.enabled ? 'raised' : ''}`}>{scalingText}</span>
      <span className="resource-bars">
        <ResourceBar label="Health" resource={follower.resources.health} kind="health" />
        <ResourceBar label="Magicka" resource={follower.resources.magicka} kind="magicka" />
        <ResourceBar label="Stamina" resource={follower.resources.stamina} kind="stamina" />
      </span>
      <span className="card-open">View ›</span>
    </button>
  );
}

export function App() {
  const [state, setState] = useState<State>(initialState);
  const [page, setPage] = useState<'roster' | 'detail'>('roster');
  const [selectedFollowerId, setSelectedFollowerId] = useState('');
  const [selectedTomeId, setSelectedTomeId] = useState('');
  const [hoveredTomeId, setHoveredTomeId] = useState('');
  const [filter, setFilter] = useState('All');

  useEffect(() => {
    window.FollowerSpellbook = {
      receiveState: (next) => {
        setState(next);
        setSelectedFollowerId((current) => next.followers.some((follower) => follower.id === current) ? current : '');
        setSelectedTomeId((current) => next.tomes.some((tome) => tome.id === current) ? current : '');
        setHoveredTomeId((current) => next.tomes.some((tome) => tome.id === current) ? current : '');
      },
    };
    send('ready');
    return () => { delete window.FollowerSpellbook; };
  }, []);

  useEffect(() => {
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        send('close');
      }
    };
    window.addEventListener('keydown', onKeyDown);
    return () => window.removeEventListener('keydown', onKeyDown);
  }, []);

  const selectedFollower = state.followers.find((follower) => follower.id === selectedFollowerId);
  const selectedTome = state.tomes.find((tome) => tome.id === selectedTomeId);
  const previewTome = state.tomes.find((tome) => tome.id === hoveredTomeId) ?? selectedTome;
  const schools = useMemo(() => {
    if (!selectedFollower) return ['All'];
    return ['All', ...Array.from(new Set(selectedFollower.spells.map((spell) => spell.school || 'Other')))];
  }, [selectedFollower]);
  const visibleSpells = selectedFollower?.spells.filter((spell) => filter === 'All' || (spell.school || 'Other') === filter) ?? [];

  const refresh = () => send('refresh');
  const close = () => send('close');
  const openFollower = (follower: Follower) => {
    setSelectedFollowerId(follower.id);
    setSelectedTomeId('');
    setFilter('All');
    setPage('detail');
  };
  const teach = () => {
    if (selectedFollower && selectedTome) {
      send('learn', { actorId: Number(selectedFollower.id), tomeId: Number(selectedTome.id) });
    }
  };
  const setLevelCap = (enabled: boolean) => {
    if (selectedFollower) send('levelCap', { actorId: Number(selectedFollower.id), enabled });
  };

  return (
    <main className="shell">
      <header className="header">
        <div>
          <p className="eyebrow">Arcane Companion Ledger</p>
          <h1>Follower Spellbook Manager</h1>
        </div>
        <button className="icon-button" onClick={close} aria-label="Close" type="button">×</button>
      </header>

      {page === 'roster' ? (
        <section className="roster-page">
          <div className="roster-heading">
            <div>
              <p className="eyebrow">Your companions</p>
              <h2>Choose a follower</h2>
              <p className="subtle">Open a companion’s spellbook to inspect or teach spells.</p>
            </div>
            <button className="small-button" onClick={refresh} type="button">Refresh</button>
          </div>
          <div className="roster-grid" aria-label="Followers">
            {state.followers.map((follower) => <FollowerCard key={follower.id} follower={follower} onOpen={() => openFollower(follower)} />)}
            {state.followers.length === 0 && <p className="empty">No current followers were found. Recruit a follower, then press Refresh.</p>}
          </div>
        </section>
      ) : (
        <section className="detail-page">
          <div className="detail-toolbar">
            <button className="back-button" onClick={() => { setPage('roster'); setSelectedFollowerId(''); }} type="button">‹ All followers</button>
            <button className="small-button" onClick={refresh} type="button">Refresh</button>
          </div>
          {selectedFollower ? (
            <>
              <div className="level-panel">
                <div className="level-panel-copy">
                  <p className="eyebrow">Level growth</p>
                  <strong>{selectedFollower.levelScaling.playerScaled ? `Player scaling ×${selectedFollower.levelScaling.multiplier.toFixed(2)}` : 'Fixed-level follower'}</strong>
                  <span>
                    {selectedFollower.levelScaling.playerScaled
                      ? `Lv.${selectedFollower.level} · original cap ${selectedFollower.levelScaling.originalMax || 'none'} · target ${selectedFollower.levelScaling.targetMax}`
                      : `Lv.${selectedFollower.level} · this follower’s authored scaling will not be changed.`}
                  </span>
                </div>
                <div className="level-panel-action">
                  <span>{selectedFollower.levelScaling.enabled ? 'Raised cap enabled' : selectedFollower.levelScaling.canToggle ? 'Use original cap' : selectedFollower.levelScaling.playerScaled ? 'Already at or above target' : 'Player scaling unavailable'}</span>
                  <button
                    className={`toggle-button ${selectedFollower.levelScaling.enabled ? 'enabled' : ''}`}
                    aria-pressed={selectedFollower.levelScaling.enabled}
                    aria-label="Raise follower level cap"
                    disabled={!selectedFollower.levelScaling.canToggle}
                    onClick={() => setLevelCap(!selectedFollower.levelScaling.enabled)}
                    type="button"
                  ><span /></button>
                  <small>A scene reload may be needed to recalculate the current level.</small>
                </div>
              </div>
              <div className="detail-content">
              <article className="spellbook">
                <div className="section-heading">
                  <div>
                    <p className="eyebrow">Known spells</p>
                    <h2>{selectedFollower.name}</h2>
                  </div>
                  <span className="count-label">{selectedFollower.spells.length} spells · {selectedFollower.maxMagicka} magicka max</span>
                </div>
                <div className="filters" aria-label="Spell school filter">
                  {schools.map((school) => <button className={filter === school ? 'active' : ''} key={school} onClick={() => setFilter(school)} type="button">{school}</button>)}
                </div>
                <div className="spell-list">
                  {visibleSpells.map((spell) => {
                    const ratio = selectedFollower.maxMagicka > 0 ? (spell.cost / selectedFollower.maxMagicka) * 100 : 0;
                    const severity = ratio > 100 ? 'unaffordable' : ratio > 60 ? 'expensive' : ratio > 25 ? 'moderate' : 'light';
                    return (
                      <div className="spell-card" key={spell.id}>
                        <div className="spell-card-heading"><strong>{spell.name}</strong><SchoolPill school={spell.school} /></div>
                        <div className="magicka-readout"><span>{spell.cost} magicka</span><span>{selectedFollower.maxMagicka > 0 ? `${Math.round(ratio)}%` : '—'}</span></div>
                        <div className="magicka-track" aria-label={`${spell.cost} of ${selectedFollower.maxMagicka} magicka`}><span className={severity} style={{ width: `${Math.min(100, Math.max(0, ratio))}%` }} /></div>
                        <small>{selectedFollower.maxMagicka > 0 ? `${spell.cost} / ${selectedFollower.maxMagicka} max magicka` : 'Maximum magicka unavailable'}</small>
                      </div>
                    );
                  })}
                  {visibleSpells.length === 0 && <p className="empty">No spells in this school.</p>}
                </div>
              </article>

              <aside className="teaching">
                <div className="section-heading">
                  <div><p className="eyebrow">Teach a spell tome</p><h2>Player inventory</h2></div>
                </div>
                <div className="tomes">
                  {state.tomes.map((tome) => (
                    <button
                      className={`tome ${selectedTomeId === tome.id ? 'selected' : ''}`}
                      key={tome.id}
                      onClick={() => setSelectedTomeId(tome.id)}
                      onMouseEnter={() => setHoveredTomeId(tome.id)}
                      onMouseLeave={() => setHoveredTomeId('')}
                      onFocus={() => setHoveredTomeId(tome.id)}
                      onBlur={() => setHoveredTomeId('')}
                      type="button"
                    >
                      <span className="tome-card-top"><span className="tome-icon">▰</span><span className="quantity">×{tome.count}</span></span>
                      <span className="tome-copy"><strong>{tome.spellName || tome.name}</strong><small>{tome.name}</small></span>
                      <span className="tome-meta"><SchoolPill school={tome.school} /><small>{tome.cost} magicka</small><small>{tome.value} gold</small></span>
                    </button>
                  ))}
                  {state.tomes.length === 0 && <p className="empty">No usable spell tomes in your inventory.</p>}
                </div>
                <div className="tome-preview" aria-live="polite">
                  <div className="preview-heading">
                    <p>{hoveredTomeId ? 'Tome details' : 'Selected tome'}</p>
                    {previewTome && <span>×{previewTome.count} · {previewTome.value} gold each</span>}
                  </div>
                  <strong>{previewTome?.spellName || previewTome?.name || 'Hover over a spell tome'}</strong>
                  <span className={previewTome?.description ? 'description' : 'description muted'}>
                    {previewTome?.description || 'Its spell description will appear here. Select a tome to teach it.'}
                  </span>
                </div>
                <button className="teach-button" disabled={!selectedFollower || !selectedTome} onClick={teach} type="button">Teach selected tome</button>
              </aside>
              </div>
            </>
          ) : <p className="empty detail-empty">This follower is no longer available. Return to the list and refresh.</p>}
        </section>
      )}

      <footer>{state.message || 'Choose a follower and a spell tome to begin.'}</footer>
    </main>
  );
}

export default App;
