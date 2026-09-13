import type { Snapshot } from "./bridge";
export function fixture():Snapshot;
export function simulate(snapshot:Snapshot,request:Record<string,unknown>):{ok:boolean;message:string};
