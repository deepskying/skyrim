import { clampQuantity } from './quantity';

export function QuantityInput({ name, count, maximum, disabled, onChange }: {
  name: string; count: number; maximum: number; disabled?: boolean; onChange: (count: number) => void;
}) {
  const limit = clampQuantity(maximum, 10000);
  const change = (value: number) => onChange(clampQuantity(value, limit));
  return <div className="quantity-input" role="group" aria-label={`${name}数量控制`}>
    <input type="number" inputMode="numeric" aria-label={`${name}数量`} min={0} max={limit} step={1} value={count} disabled={disabled || !limit}
      onFocus={e => e.currentTarget.select()} onChange={e => change(Number(e.target.value))}
      onKeyDown={e => { if (e.key === 'Enter') e.currentTarget.blur(); }} />
  </div>;
}
