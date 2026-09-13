import type {GameFollower} from './bridge';

const icons={
 health:'M12 20S3 14 3 8a5 5 0 0 1 9-3 5 5 0 0 1 9 3c0 6-9 12-9 12Z',
 magicka:'m12 2 3 7 7 3-7 3-3 7-3-7-7-3 7-3Z',
 stamina:'m13 2-8 12h6l-1 8 9-13h-6Z'
};

export function CompanionVitals({f}:{f:GameFollower}){
 return <div className="cm-vitals">{(['health','magicka','stamina'] as const).map((key,i)=>{
   const [value,max]=f[key];
   const ratio=max>0?Math.max(0,Math.min(100,value/max*100)):0;
   const label=['生命','法力','体力'][i];
   const text=`${Math.round(value)} / ${Math.round(max)}`;
   return <div key={key} className={`cm-vital-row cm-vital-${key}`}>
     <div className="cm-vital-caption"><span className="cm-vital-label"><svg viewBox="0 0 24 24" aria-hidden="true"><path d={icons[key]}/></svg>{label}</span><strong>{Math.round(value)} <small>/ {Math.round(max)}</small></strong></div>
     <div className="cm-vital-track" role="progressbar" aria-label={label} aria-valuemin={0} aria-valuemax={100} aria-valuenow={ratio} aria-valuetext={text}>
       <span style={{width:`${ratio}%`}}/>
     </div>
   </div>;
 })}</div>;
}
