export type DismantleHotkey = { key: string; shift: boolean; ctrl: boolean; alt: boolean; enabled: boolean };
export const defaultDismantleHotkey: DismantleHotkey = { key: 'D', shift: true, ctrl: false, alt: false, enabled: true };
export function shortcutLabel(binding: DismantleHotkey) {
  return [binding.ctrl && 'Ctrl', binding.shift && 'Shift', binding.alt && 'Alt', binding.key].filter(Boolean).join(' + ');
}
export function shortcutAllowed(context: { visible: boolean; page: string; forge: boolean; editing: boolean; busy: boolean; protectedItem: boolean; selectedId?: string; eventId?: string }) {
  return context.visible && context.page === 'dismantle' && context.forge && !context.editing && !context.busy && !context.protectedItem && !!context.selectedId && context.selectedId === context.eventId;
}
export function matchesShortcut(event: { key: string; shiftKey: boolean; ctrlKey: boolean; altKey: boolean; repeat: boolean; isComposing?: boolean }, binding: DismantleHotkey) {
  return binding.enabled && !event.repeat && !event.isComposing && event.key.toUpperCase() === binding.key.toUpperCase() && event.shiftKey === binding.shift && event.ctrlKey === binding.ctrl && event.altKey === binding.alt;
}
