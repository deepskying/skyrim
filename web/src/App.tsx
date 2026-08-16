import { useEffect, useMemo, useState } from 'react';
import './styles.css';

type Spell = {
  id: string;
  name: string;
  school: string;
  cost: number;
};

type Follower = {
  id: string;
  name: string;
  maxMagicka: number;
  spells: Spell[];
};

type Tome = Spell & { count: number };

type State = {
  followers: Follower[];
  tomes: Tome[];
  status: string;
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
    { id: 'demo-lydia', name: 'Lydia', maxMagicka: 100, spells: [{ id: 'ice-spike', name: 'Ice Spike', school: 'Destruction', cost: 30 }] },
    { id: 'demo-serana', name: 'Serana', maxMagicka: 220, spells: [{ id: 'firebolt', name: 'Firebolt', school: 'Destruction', cost: 25 }] },
  ],
  tomes: [
    { id: 'firebolt-tome', name: 'Firebolt', school: 'Destruction', cost: 25, count: 1 },
    { id: 'fast-healing-tome', name: 'Fast Healing', school: 'Restoration', cost: 73, count: 2 },
  ],
  status: 'Choose a follower and a spell tome to begin.',
};

const empty: State = { followers: [], tomes: [], status: 'Loading follower data…' };
const initialState = import.meta.env.DEV ? demo : empty;

function send(type: string, data: Record<string, unknown> = {}) {
  if (typeof window.followerSpellbookAction !== 'function') return;
  window.followerSpellbookAction(JSON.stringify({ type, ...data }));
}

function SchoolPill({ school }: { school: string }) {
  return <span className="school">{school || 'Other'}</span>;
}

function FollowerCard({ follower, onOpen }: { follower: Follower; onOpen: () => void }) {
  return (
    <button className="follower-card" onClick={onOpen} type="button">
      <span className="card-sigil">✦</span>
      <span className="follower-card-copy">
        <strong>{follower.name}</strong>
        <small>{follower.spells.length} known spells</small>
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
  const [filter, setFilter] = useState('All');

  useEffect(() => {
    window.FollowerSpellbook = {
      receiveState: (next) => {
        setState(next);
        setSelectedFollowerId((current) => next.followers.some((follower) => follower.id === current) ? current : '');
        setSelectedTomeId((current) => next.tomes.some((tome) => tome.id === current) ? current : '');
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
                    <button className={`tome ${selectedTomeId === tome.id ? 'selected' : ''}`} key={tome.id} onClick={() => setSelectedTomeId(tome.id)} type="button">
                      <span className="tome-icon">▰</span>
                      <span><strong>{tome.name}</strong><small><SchoolPill school={tome.school} /> · {tome.cost} magicka · ×{tome.count}</small></span>
                    </button>
                  ))}
                  {state.tomes.length === 0 && <p className="empty">No usable spell tomes in your inventory.</p>}
                </div>
                <div className="selection">
                  <p>Selected tome</p>
                  <strong>{selectedTome ? `Spell Tome: ${selectedTome.name}` : 'No tome selected'}</strong>
                  <span>The tome is consumed only after learning succeeds.</span>
                </div>
                <button className="teach-button" disabled={!selectedFollower || !selectedTome} onClick={teach} type="button">Teach selected tome</button>
              </aside>
            </div>
          ) : <p className="empty detail-empty">This follower is no longer available. Return to the list and refresh.</p>}
        </section>
      )}

      <footer>{state.status}</footer>
    </main>
  );
}

export default App;
