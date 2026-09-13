export type WorkshopAction = (type: string, data?: Record<string, unknown>) => void;
export function send(type: string, data: Record<string, unknown> = {}) {
  window.durabilityManagerAction?.(JSON.stringify({ type, ...data }));
}
export const sendArrowAction: WorkshopAction = (type, data = {}) => send('arrows', { action: { type, ...data } });
