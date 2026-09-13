export type HudMessage = {
  id: number; kind: 'weapon' | 'warning'; title: string; detail: string;
  durationMilliseconds: number; current?: number; maximum?: number;
};

const finite = (value: unknown): value is number => typeof value === 'number' && Number.isFinite(value);

export type EquippedHudItem = {
  id: string; kind: 'weapon' | 'warning'; title: string; detail: string;
  current: number; maximum: number;
};

// Full snapshots replace the previous list, including [] after unequip or menus.
export function normalizeEquippedHud(value: unknown): EquippedHudItem[] | undefined {
  if (!Array.isArray(value)) return undefined;
  const seen = new Set<string>();
  const items: EquippedHudItem[] = [];
  for (const raw of value) {
    if (!raw || typeof raw !== 'object' || typeof raw.id !== 'string' || !raw.id || seen.has(raw.id) ||
        (raw.kind !== 'weapon' && raw.kind !== 'warning') || typeof raw.title !== 'string' ||
        !finite(raw.current) || !finite(raw.maximum) || raw.maximum <= 0) continue;
    seen.add(raw.id);
    items.push({ id: raw.id, kind: raw.kind, title: raw.title,
      detail: typeof raw.detail === 'string' ? raw.detail : '',
      current: Math.max(0, Math.min(raw.maximum, raw.current)), maximum: raw.maximum });
  }
  return items;
}

export function normalizeHudMessage(value: unknown): HudMessage | undefined {
  if (typeof value !== 'object' || value === null || Array.isArray(value)) return undefined;
  const raw = value as Record<string, unknown>;
  if (!finite(raw.id) || !Number.isInteger(raw.id) || raw.id < 0 || raw.id > 0xffffffff ||
      (raw.kind !== 'weapon' && raw.kind !== 'warning')) return undefined;
  const message: HudMessage = {
    id: raw.id, kind: raw.kind,
    title: typeof raw.title === 'string' ? raw.title : '装备耐久',
    detail: typeof raw.detail === 'string' ? raw.detail : '',
    durationMilliseconds: finite(raw.durationMilliseconds)
      ? Math.round(Math.max(500, Math.min(10000, raw.durationMilliseconds))) : 3000,
  };
  // Invalid/missing durability is a text-only notification, never a 0/0 bar.
  if (finite(raw.maximum) && raw.maximum > 0 && finite(raw.current)) {
    message.maximum = raw.maximum;
    message.current = Math.max(0, Math.min(raw.maximum, raw.current));
  }
  return message;
}

export function createHudReceiver(
  display: (message: HudMessage | undefined) => void,
  hidden: (id: number) => void,
  timers: { set: (callback: () => void, delay: number) => number; clear: (id: number) => void },
) {
  let timer: number | undefined;
  let generation = 0;
  let disposed = false;
  return {
    receive(value: unknown) {
      if (disposed) return;
      const message = normalizeHudMessage(value);
      if (!message) return; // Do not cancel a valid HUD/timer for malformed input.
      const currentGeneration = ++generation;
      if (timer !== undefined) timers.clear(timer);
      display(message);
      timer = timers.set(() => {
        if (disposed || currentGeneration !== generation) return;
        timer = undefined;
        display(undefined);
        hidden(message.id);
      }, message.durationMilliseconds);
    },
    clear() {
      ++generation;
      if (timer !== undefined) timers.clear(timer);
      timer = undefined;
      display(undefined);
    },
    dispose() {
      disposed = true;
      ++generation;
      if (timer !== undefined) timers.clear(timer);
      timer = undefined;
    },
  };
}
