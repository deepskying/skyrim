// One faceted gem silhouette, recoloured per soul tier. Petty gems stay small and pale,
// grand turns warm gold and the black gem keeps a dark violet body so the cards can be
// told apart at a glance without shipping icon assets.
type Palette = { light: string; mid: string; dark: string; edge: string; table: string };
const palettes: Record<number, Palette> = {
  1: { light: '#e6f4f0', mid: '#b3d3cb', dark: '#6f968e', edge: '#9dc0b8', table: '#ffffff' },
  2: { light: '#dceaff', mid: '#9cc6f2', dark: '#4f7398', edge: '#8fb6dd', table: '#ffffff' },
  3: { light: '#dcf6e8', mid: '#93d9b8', dark: '#3f7f63', edge: '#87c5a7', table: '#ffffff' },
  4: { light: '#e4e9ff', mid: '#adbaf2', dark: '#5c66a8', edge: '#a2ade6', table: '#ffffff' },
  5: { light: '#fff1cc', mid: '#e9cb79', dark: '#95762b', edge: '#d8b662', table: '#fff8e2' },
  6: { light: '#e6d4ff', mid: '#9a6fd8', dark: '#2f1747', edge: '#7d5bb0', table: '#c9aef0' },
};
const filledGems: Record<number, number> = {
  0x2E4E3: 1, 0x2E4E5: 2, 0x2E4F3: 3, 0x2E4FB: 4, 0x2E4FF: 5, 0x2E504: 6,
};
export function levelForGem(formID: number) { return filledGems[formID] ?? 0; }
export function SoulGemIcon({ level }: { level: number }) {
  const palette = palettes[level] ?? palettes[3];
  const gradient = `soulGemBody${level}`;
  const table = `soulGemTable${level}`;
  return <svg viewBox="0 0 64 64" className={`soul-gem-svg level-${level}`} aria-hidden="true" focusable="false">
    <defs>
      <linearGradient id={gradient} x1="10%" y1="0%" x2="80%" y2="100%">
        <stop offset="0%" stopColor={palette.light} />
        <stop offset="55%" stopColor={palette.mid} />
        <stop offset="100%" stopColor={palette.dark} />
      </linearGradient>
      <linearGradient id={table} x1="0%" y1="0%" x2="0%" y2="100%">
        <stop offset="0%" stopColor={palette.table} stopOpacity=".92" />
        <stop offset="100%" stopColor={palette.mid} stopOpacity=".75" />
      </linearGradient>
    </defs>
    <path d="M20 7h24l11 15-23 35L9 22Z" fill={`url(#${gradient})`} stroke={palette.edge} strokeWidth="1.6" strokeLinejoin="round" />
    <path d="M20 7h24l11 15H9Z" fill={`url(#${table})`} stroke={palette.edge} strokeWidth="1.1" strokeLinejoin="round" />
    <path d="M32 22v35M9 22l23 35M55 22 32 57M20 7 9 22M44 7l11 15" fill="none" stroke={palette.edge} strokeWidth="1" strokeLinejoin="round" opacity=".7" />
    <path d="M15 13.5 20.5 9.5" fill="none" stroke={palette.table} strokeWidth="2.4" strokeLinecap="round" opacity=".85" />
  </svg>;
}
