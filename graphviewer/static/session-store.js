const key='graphviewer-session-v1';
const views=['architecture','files','classes','functions','folders','languages'];
export function loadSession(storage){
 try{
  const s=JSON.parse(storage.getItem(key)||'null');
  if(!s||!views.includes(s.view)||typeof s.source!=='string'||!Number.isInteger(s.depth)||s.depth<1||s.depth>10)return null;
  if(s.core!==null&&typeof s.core!=='string')return null;
  const v=s.viewport;
  if(!v||!Number.isFinite(v.scale)||v.scale<.01||v.scale>4||!Number.isFinite(v.pan?.x)||!Number.isFinite(v.pan?.y))return null;
  if ('trail' in s) {
    const valid=Array.isArray(s.trail)&&s.trail.every(n=>n&&typeof n.key==='string'&&typeof n.name==='string'&&views.includes(n.category));
    const cursorValid=Number.isInteger(s.trailIndex)&&s.trailIndex>=0&&s.trailIndex<s.trail?.length;
    const current=valid&&cursorValid?s.trail[s.trailIndex]:null;
    if(!current||current.key!==s.core||current.category!==s.view){s.trail=[];s.trailIndex=-1;}
  }
  if ('history' in s && (!Array.isArray(s.history)||!s.history.every(n=>n&&views.includes(n.view)&&(n.core===null||typeof n.core==='string'))))s.history=[];
  return s;
 }catch{return null;}
}
export function saveSession(storage,session){try{storage.setItem(key,JSON.stringify(session));return true;}catch{return false;}}
