// The native snapshot lists companions ordered by live distance, so anything that reads the first
// entry re-targets the panel whenever somebody walks closer. The selection therefore only ever
// changes when the player or a dialogue asks for somebody: an empty selection seeds from the
// roster, and a companion that left the roster keeps the panel waiting instead of silently
// switching to whoever happens to be first now.
export function pinnedCompanionId(current: string, roster: { id: string }[]): string {
  if (current) return current;
  return roster[0]?.id ?? "";
}
