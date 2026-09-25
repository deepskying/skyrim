import {useEffect,useRef,useState} from "react";
import {previewLabel,type PreviewStatus} from "./wear";
import "./outfits.css";

// The 3D area is an empty viewport: Meridian's NifView draws its surface over exactly this
// rectangle, so nothing but the placeholder may live inside it. The native side owns the model and
// the camera; this component only reports the rectangle and asks for the status.
const send=(type:string,data:Record<string,unknown>={})=>
  typeof window.companionRequest==="function"&&window.companionRequest(JSON.stringify({type,...data}));
let nextToken=0;

type Props={actorId:string;id:string};

export function ModelPreview({actorId,id}:Props){
  const viewport=useRef<HTMLDivElement>(null);
  const camera=useRef({yaw:35,pitch:15,distance:1});
  const drag=useRef<{x:number;y:number}|null>(null);
  const [status,setStatus]=useState<PreviewStatus>("empty");
  useEffect(()=>{
    const element=viewport.current;
    if(!element||!id||!actorId){setStatus("empty");send("previewClear");return;}
    const token=++nextToken;
    setStatus("loading");
    camera.current={yaw:35,pitch:15,distance:1};
    send("previewSelect",{actorId,id});
    const layout=()=>{
      const rect=element.getBoundingClientRect();
      const visible=rect.left>=0&&rect.top>=0&&rect.right<=window.innerWidth&&rect.bottom<=window.innerHeight;
      // A viewport that is partly scrolled out of the panel is reported as zero-sized, which keeps
      // the surface hidden instead of drawing a model over unrelated UI.
      send("previewLayout",{x:Math.round(rect.left),y:Math.round(rect.top),width:visible?Math.round(rect.width):0,height:Math.round(rect.height)});
    };
    const receive=(event:Event)=>{
      const detail=(event as CustomEvent).detail;
      if(detail?.id===id&&detail?.token===token)setStatus(detail.status as PreviewStatus);
    };
    window.addEventListener("companion:preview-status",receive);
    window.addEventListener("resize",layout);
    const observer=new ResizeObserver(layout);
    observer.observe(element);
    layout();
    const poll=()=>send("previewStatus",{id,token});
    poll();
    const timer=window.setInterval(poll,250);
    return ()=>{
      window.clearInterval(timer);
      observer.disconnect();
      window.removeEventListener("resize",layout);
      window.removeEventListener("companion:preview-status",receive);
      send("previewClear");
    };
  },[actorId,id]);
  const reset=()=>{camera.current={yaw:35,pitch:15,distance:1};send("previewCamera",camera.current);};
  return <section className="cm-preview" aria-label="装备模型预览">
    <div className="cm-preview-viewport" ref={viewport}
      onPointerDown={event=>{
        if(event.button!==0)return;
        event.currentTarget.setPointerCapture(event.pointerId);
        drag.current={x:event.clientX,y:event.clientY};
      }}
      onPointerMove={event=>{
        if(!drag.current)return;
        camera.current.yaw=(camera.current.yaw+(event.clientX-drag.current.x)*0.6)%360;
        camera.current.pitch=Math.max(-85,Math.min(85,camera.current.pitch+(event.clientY-drag.current.y)*0.6));
        drag.current={x:event.clientX,y:event.clientY};
        send("previewCamera",camera.current);
      }}
      onPointerUp={()=>{drag.current=null;}}
      onLostPointerCapture={()=>{drag.current=null;}}
      onWheel={event=>{
        camera.current.distance=Math.max(0.25,Math.min(4,camera.current.distance*Math.exp(event.deltaY*0.001)));
        send("previewCamera",camera.current);
      }}>
      {status!=="ready"&&<span className="cm-preview-placeholder" aria-hidden="true">◈</span>}
    </div>
    <div className="cm-preview-bar"><span role="status">{previewLabel(status)}</span><button type="button" disabled={status!=="ready"} onClick={reset}>重置视角</button></div>
  </section>;
}
