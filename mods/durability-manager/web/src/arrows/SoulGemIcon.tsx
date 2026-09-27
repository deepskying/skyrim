// A plain diamond, drawn instead of a font glyph so it stays centred and keeps its shape at
// any panel scale. The tier only changes the colour and size, not the geometry.
type Palette = { light: string; mid: string; dark: string; edge: string };
const palettes: Record<number, Palette> = {
  1: { light: '#e6f4f0', mid: '#b3d3cb', dark: '#6f968e', edge: '#9dc0b8' },
  2: { light: '#dceaff', mid: '#9cc6f2', dark: '#4f7398', edge: '#8fb6dd' },
  3: { light: '#dcf6e8', mid: '#93d9b8', dark: '#3f7f63', edge: '#87c5a7' },
  4: { light: '#e4e9ff', mid: '#adbaf2', dark: '#5c66a8', edge: '#a2ade6' },
  5: { light: '#fff1cc', mid: '#e9cb79', dark: '#95762b', edge: '#d8b662' },
  6: { light: '#e6d4ff', mid: '#9a6fd8', dark: '#2f1747', edge: '#7d5bb0' },
};
const filledGems: Record<number, number> = {
  0x2E4E3: 1, 0x2E4E5: 2, 0x2E4F3: 3, 0x2E4FB: 4, 0x2E4FF: 5, 0x2E504: 6,
};
export function levelForGem(formID: number) { return filledGems[formID] ?? 0; }
export function SoulGemIcon({ level }: { level: number }) {
  const palette = palettes[level] ?? palettes[3];
  const gradient = `soulGemBody${level}`;
  return <svg viewBox="0 0 64 64" className={`soul-gem-svg level-${level}`} aria-hidden="true" focusable="false">
    <defs>
      <linearGradient id={gradient} x1="10%" y1="0%" x2="80%" y2="100%">
        <stop offset="0%" stopColor={palette.light} />
        <stop offset="60%" stopColor={palette.mid} />
        <stop offset="100%" stopColor={palette.dark} />
      </linearGradient>
    </defs>
    <path d="M32 5 59 32 32 59 5 32Z" fill={`url(#${gradient})`} stroke={palette.edge} strokeWidth="1.8" strokeLinejoin="round" />
  </svg>;
}
