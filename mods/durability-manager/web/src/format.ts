// Display only: keep the original values for progress, repair checks and saves.
export function formatDurability(value: number | undefined): string {
  return typeof value === 'number' && Number.isFinite(value) ? value.toFixed(1) : '—';
}
