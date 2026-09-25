import { useLayoutEffect, useRef, useState, type ReactNode } from 'react';
import { hudOffsets, normalizeHudPosition } from './hud';

export function HudFrame({ position, children }: { position: ReturnType<typeof normalizeHudPosition>; children: ReactNode }) {
  const ref = useRef<HTMLDivElement>(null);
  const [size, setSize] = useState({ width: window.innerWidth, height: window.innerHeight, itemWidth: 0, itemHeight: 0 });
  useLayoutEffect(() => {
    const measure = () => {
      const bounds = ref.current?.getBoundingClientRect();
      setSize({ width: window.innerWidth, height: window.innerHeight, itemWidth: bounds?.width ?? 0, itemHeight: bounds?.height ?? 0 });
    };
    const observer = new ResizeObserver(measure);
    if (ref.current) observer.observe(ref.current);
    window.addEventListener('resize', measure);
    measure();
    return () => { observer.disconnect(); window.removeEventListener('resize', measure); };
  }, []);
  return <div ref={ref} className="durability-hud-stack" style={hudOffsets(position, size.width, size.height, size.itemWidth, size.itemHeight)}>{children}</div>;
}
