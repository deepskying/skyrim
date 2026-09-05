export function EquippedBadge({ equipped }: { equipped: boolean }) {
  return equipped ? <span className="equipped-badge">✓ 已装备</span> : null;
}
