import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import { SoulPoolPage } from './arrows/SoulPool';
import { arrowDemo } from './arrows/demo';
import './styles.css';
import './workshop.css';
import './arrows/arrows.css';

// Dev-only page (vite build only reads index.html): open /soul-preview.html to review the
// soul pool page with the sample data, without stepping through the rail.
const preview = <div className="forge-shell arrows-active" style={{ '--workshop-font-scale': 1, '--workshop-background-alpha': 1 } as React.CSSProperties}>
  <div className="workshop-workspace"><SoulPoolPage state={arrowDemo} action={() => {}} active /></div>
</div>;

createRoot(document.getElementById('root')!).render(<StrictMode>{preview}</StrictMode>);
