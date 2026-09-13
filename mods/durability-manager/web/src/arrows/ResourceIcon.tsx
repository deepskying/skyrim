export type ResourceKind = 'gold' | 'mana' | 'charge';

export function ResourceIcon({ kind }: { kind: ResourceKind }) {
  return <svg className={`craft-cost-icon ${kind}`} viewBox="0 0 24 24" aria-hidden="true" focusable="false">
    {kind === 'gold' && <><circle cx="12" cy="12" r="9" /><circle cx="12" cy="12" r="6" /><path d="m12 8 3 4-3 4-3-4Z" /></>}
    {kind === 'mana' && <><path d="M12 2c-2 4-7 9-7 13a7 7 0 0 0 14 0c0-4-5-9-7-13Z" /><path d="m12 10 1.2 3.8L17 15l-3.8 1.2L12 20l-1.2-3.8L7 15l3.8-1.2Z" /></>}
    {kind === 'charge' && <path d="M14 2 4 14h7l-1 8 10-12h-7Z" />}
  </svg>;
}
