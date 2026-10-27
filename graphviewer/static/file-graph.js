import { networkPositions } from './network-layout.js';
import { Graph } from './graph.js?v=session-1';
import { loadLayout } from './layout-store.js';
const NS='http://www.w3.org/2000/svg';
function el(tag,attrs={},text=''){const n=document.createElementNS(NS,tag);for(const [k,v]of Object.entries(attrs))n.setAttribute(k,v);n.textContent=text;return n;}
export class FileGraph extends Graph {
 render(data,reset=true){
  const start=performance.now();this.data=data;this.layer.replaceChildren();
  this.width=this.svg.clientWidth||800;this.height=this.svg.clientHeight||500;
  this.svg.setAttribute('viewBox',`0 0 ${this.width} ${this.height}`);
  this.nodeWidth=112;this.positions=new Map();
  this.positions=networkPositions(data.nodes,data.edges,this.width,this.height);
  this.savedPositions=loadLayout(localStorage,data.layoutKey,this.width,this.height);
  for(const [k,p]of this.savedPositions)if(this.positions.has(k))this.positions.set(k,p);
  this.edgeLayer=el('g');this.layer.append(this.edgeLayer);this.drawEdges(data.edges,this.positions);
  for(const n of data.nodes)this.drawCompact(n);
  this.visibleCount=data.visible_files;
  if(reset)this.fit();else this.transform();
  this.renderMs=performance.now()-start;
 }
 fit(){if(!this.data?.layered)return super.fit();
  const p=[...this.positions.values()];if(!p.length)return;
  const minX=Math.min(...p.map(v=>v.x))-70,maxX=Math.max(...p.map(v=>v.x))+70;
  const minY=Math.min(...p.map(v=>v.y))-35,maxY=Math.max(...p.map(v=>v.y))+35;
  this.scale=Math.min(1.3,(this.width-30)/(maxX-minX),(this.height-30)/(maxY-minY));
  this.pan={x:(this.width/2-(minX+maxX)/2)*this.scale,y:(this.height/2-(minY+maxY)/2)*this.scale};this.transform();
 }
 zoom(delta){this.scale=Math.max(.05,Math.min(4,this.scale+delta));this.transform();}
 drawCompact(node){const p=this.positions.get(node.key),hidden=node.category==='hidden',core=node.key===this.data.core.key;
  const caption=node.display_name||node.name;
  const g=el('g',{class:'graph-node compact-node'+(core?' core':'')+(hidden?' hidden-node':''),transform:`translate(${p.x},${p.y})`,tabindex:0,role:'button','aria-label':hidden?`${node.hidden_count} hidden neighbors`:`${caption}. Double click to make Master`,style:`--node-accent:${core?'#078f88':hidden?'#8b6db5':node.level===1?'#48926f':'#5c83b4'}`});g.dataset.key=node.key;
  g.append(el('rect',{class:'node-shell',x:-56,y:-12,width:112,height:24,rx:hidden?12:4}));
  const mainLabel=node.category==='methods'?node.name:caption;
  g.append(el('text',{x:0,y:node.category==='methods'?0:4,'text-anchor':'middle',class:'compact-name'},mainLabel.length>17?mainLabel.slice(0,15)+'…':mainLabel));
  if(node.category==='methods')g.append(el('text',{x:0,y:9,'text-anchor':'middle',class:'method-class-name'},(node.class_name||node.parent_name||'').slice(0,24)));

  g.append(el('title',{},hidden?`${node.hidden_count} hidden elements beyond the selected visible depth. Each hidden element belongs to exactly one group.`:`${node.name}\n${node.file_path||node.path}`));
  {
   g.addEventListener('pointerdown',e=>this.startNodeDrag(e,node,g));
   g.addEventListener('click',()=>{if(performance.now()>=(this.suppressClickUntil||0))this.select(node);});
   g.addEventListener('dblclick',event=>{event.preventDefault();if(performance.now()>=(this.suppressClickUntil||0))this.onExplore(node,event);});
   g.addEventListener('keydown',e=>{if(e.key==='Enter')this.select(node);if(e.key==='ArrowRight')this.onExplore(node);});
   g.addEventListener('pointerenter',()=>this.highlight(node.key));g.addEventListener('pointerleave',()=>this.highlight(null));
  }this.layer.append(g);
 }
 highlight(key){for(const p of this.edgeLayer.children){const active=!key||p.dataset.source===key||p.dataset.target===key;p.style.opacity=active?'0.7':'0.06';}}
 drawEdges(edges,positions){for(const e of edges){const a=positions.get(e.source),b=positions.get(e.target);if(!a||!b)continue;
  const dx=b.x-a.x,dy=b.y-a.y;
  const exit=Math.min(56/Math.max(.001,Math.abs(dx)),12/Math.max(.001,Math.abs(dy)));
  const sx=a.x+dx*exit,sy=a.y+dy*exit,tx=b.x-dx*exit,ty=b.y-dy*exit;
  const len=Math.max(1,Math.hypot(dx,dy)),curve=9;
  const path=el('path',{d:`M${sx},${sy} Q${(sx+tx)/2-dy/len*curve},${(sy+ty)/2+dx/len*curve} ${tx},${ty}`,class:'graph-edge','marker-end':`url(#${this.arrowId||'arrow'})`});
  path.append(el('title',{},`${e.kind} · ${e.count} indexed relations`));
  if(e.kind==='HIDDEN')path.setAttribute('stroke-dasharray','3 4');path.dataset.source=e.source;path.dataset.target=e.target;this.edgeLayer.append(path);
 }}
}
