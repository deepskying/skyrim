// Two concentric diamond outlines - an inner and an outer ring - drawn instead of a font
// glyph so they stay centred and keep their shape at any panel scale. The stroke follows
// currentColor so every card shows the same colour and size.
export function SoulGemIcon() {
  return <svg viewBox="0 0 64 64" className="soul-gem-svg" aria-hidden="true" focusable="false">
    <path d="M32 4 60 32 32 60 4 32Z" fill="none" stroke="currentColor" strokeWidth="4.5" strokeLinejoin="round" />
    <path d="M32 17 47 32 32 47 17 32Z" fill="none" stroke="currentColor" strokeWidth="4.5" strokeLinejoin="round" />
  </svg>;
}
