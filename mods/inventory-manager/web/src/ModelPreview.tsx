import { useEffect, useRef, useState } from 'react';
import { Icon } from './icon';

const send = (type: string, data: Record<string, unknown> = {}) =>
  window.inventoryManagerAction?.(JSON.stringify({ type, ...data }));
let nextToken = 0;

export function ModelPreview({ id, icon, enabled }: { id: number; icon: string; enabled: boolean }) {
  const viewport = useRef<HTMLDivElement>(null);
  const camera = useRef({ yaw: 35, pitch: 15, distance: 1 });
  const drag = useRef<{ x: number; y: number }>();
  const [status, setStatus] = useState('loading');
  const [generation, setGeneration] = useState(0);

  useEffect(() => {
    const refresh = () => setGeneration(value => value + 1);
    window.addEventListener('inventory-preview-refresh', refresh);
    return () => window.removeEventListener('inventory-preview-refresh', refresh);
  }, []);

  useEffect(() => {
    const element = viewport.current;
    if (!enabled || !element) return;
    const token = ++nextToken;
    setStatus('loading');
    camera.current = { yaw: 35, pitch: 15, distance: 1 };
    send('previewSelect', { id });
    const layout = () => {
      const rect = element.getBoundingClientRect();
      const visible = rect.left >= 0 && rect.top >= 0 && rect.right <= window.innerWidth && rect.bottom <= window.innerHeight;
      send('previewLayout', { x: Math.round(rect.left), y: Math.round(rect.top), width: visible ? Math.round(rect.width) : 0, height: Math.round(rect.height) });
    };
    const receive = (event: Event) => {
      const detail = (event as CustomEvent).detail;
      if (detail?.id === id && detail?.token === token) setStatus(detail.status);
    };
    window.addEventListener('inventory-preview-status', receive);
    window.addEventListener('resize', layout);
    const observer = new ResizeObserver(layout);
    observer.observe(element);
    layout();
    const poll = () => send('previewStatus', { id, token });
    poll();
    const timer = window.setInterval(poll, 250);
    return () => {
      clearInterval(timer);
      observer.disconnect();
      window.removeEventListener('resize', layout);
      window.removeEventListener('inventory-preview-status', receive);
      send('previewClear');
    };
  }, [id, enabled, generation]);

  const reset = () => {
    camera.current = { yaw: 35, pitch: 15, distance: 1 };
    send('previewCamera', camera.current);
  };
  const label = !enabled ? '模型预览未连接' : status === 'loading' ? '正在加载模型…' : status === 'ready' ? '拖动旋转 · 滚轮缩放' : status === 'failed' ? '模型加载失败' : '此物品暂不支持模型预览';

  return <section className="model-preview" aria-label="物品模型预览">
    <div className="model-viewport" ref={viewport}
      onPointerDown={event => {
        if (event.button !== 0) return;
        event.currentTarget.setPointerCapture(event.pointerId);
        drag.current = { x: event.clientX, y: event.clientY };
      }}
      onPointerMove={event => {
        if (!drag.current) return;
        camera.current.yaw = (camera.current.yaw + (event.clientX - drag.current.x) * 0.6) % 360;
        camera.current.pitch = Math.max(-85, Math.min(85, camera.current.pitch + (event.clientY - drag.current.y) * 0.6));
        drag.current = { x: event.clientX, y: event.clientY };
        send('previewCamera', camera.current);
      }}
      onPointerUp={() => { drag.current = undefined; }}
      onLostPointerCapture={() => { drag.current = undefined; }}
      onWheel={event => {
        camera.current.distance = Math.max(0.25, Math.min(4, camera.current.distance * Math.exp(event.deltaY * 0.001)));
        send('previewCamera', camera.current);
      }}>
      {(!enabled || status !== 'ready') && <Icon name={icon} />}
    </div>
    <div className="preview-toolbar"><span role="status">{label}</span><button type="button" disabled={!enabled || status !== 'ready'} onClick={reset}>重置视角</button></div>
  </section>;
}
