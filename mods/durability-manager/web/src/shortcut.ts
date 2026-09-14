export type ShortcutBinding = { key: string; shift: boolean; ctrl: boolean; alt: boolean; enabled: boolean };
export function matchesShortcut(event: { key: string; shiftKey: boolean; ctrlKey: boolean; altKey: boolean; repeat: boolean; isComposing?: boolean }, binding: ShortcutBinding) {
  return binding.enabled && !event.repeat && !event.isComposing && event.key.toUpperCase() === binding.key.toUpperCase() && event.shiftKey === binding.shift && event.ctrlKey === binding.ctrl && event.altKey === binding.alt;
}
