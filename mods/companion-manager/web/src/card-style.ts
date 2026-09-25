// Card surfaces must stay translucent: the player watches the companion behind the window while
// dressing them, so a card only needs enough tint for text contrast. The alpha follows the
// panel-opacity preference inside bounds that stay readable and never become opaque.
export function cardAlpha(opacityPercent: number): number {
  const value = (Number.isFinite(opacityPercent) ? opacityPercent : 82) / 100 - 0.26;
  // Rounded so the generated CSS colour stays stable and readable in logs.
  return Math.round(Math.min(0.72, Math.max(0.34, value)) * 100) / 100;
}

export function cardStrongAlpha(alpha: number): number {
  return Math.min(0.9, alpha + 0.22);
}
