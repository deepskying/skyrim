import { clampQuantity } from './quantity';

export function QuantitySlider({ name, count, maximum, disabled, onChange }: {
  name: string; count: number; maximum: number; disabled?: boolean; onChange: (count: number) => void;
}) {
  const limit = Math.max(0, Math.floor(maximum));
  const change = (value: number) => onChange(clampQuantity(value, limit));
  return <div className="quantity-slider">
    <input type="range" aria-label={`${name}数量滑块`} min="0" max={limit} step="1" value={Math.min(count, limit)} disabled={disabled || !limit} onChange={e => change(Number(e.target.value))} />
    <input type="number" aria-label={`${name}数量`} min="0" max={limit} step="1" value={count} disabled={disabled || !limit} onChange={e => change(Number(e.target.value))} onKeyDown={e => { if (e.key === 'Enter') e.currentTarget.blur(); }} />
    <span>/ {limit}</span>
  </div>;
}
