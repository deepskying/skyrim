// An outlined diamond, drawn instead of a font glyph so it stays centred and keeps its
// shape at any panel scale. No fill: the tier only changes the stroke colour and size.
const strokes: Record<number, string> = {
  1: '#c3d9d3', 2: '#9cc6f2', 3: '#93d9b8', 4: '#aeb9f2', 5: '#e9cb79', 6: '#b183ee',
};
const filledGems: Record<number, number> = {
  0x2E4E3: 1, 0x2E4E5: 2, 0x2E4F3: 3, 0x2E4FB: 4, 0x2E4FF: 5, 0x2E504: 6,
};
export function levelForGem(formID: number) { return filledGems[formID] ?? 0; }
export function SoulGemIcon({ level }: { level: number }) {
  return <svg viewBox="0 0 64 64" className={`soul-gem-svg level-${level}`} aria-hidden="true" focusable="false">
    <path d="M32 6 58 32 32 58 6 32Z" fill="none" stroke={strokes[level] ?? strokes[3]} strokeWidth="3" strokeLinejoin="round" />
  </svg>;
}
