import { api, element } from './api.js';
import { FileGraph } from './file-graph.js?v=all-views-2';
import { openCode } from './code-view.js';

export class MethodExplorer {
 constructor(context){
  this.context=context;this.ticket=0;
  this.dialog=element('dialog','method-dialog');this.dialog.setAttribute('aria-label','Class methods explorer');
  const header=element('div','dialog-top');this.title=element('h2','','Class methods');const close=element('button','icon-button','×');close.setAttribute('aria-label','Close methods explorer');close.onclick=()=>this.dialog.close();header.append(this.title,close);
  this.toolbar=element('div','method-toolbar');this.depth=element('select');this.depth.setAttribute('aria-label','Method graph levels');for(let i=1;i<=10;i++){const o=element('option','',String(i));o.value=i;this.depth.append(o);}this.depth.value='2';this.depth.onchange=()=>this.load(this.master,false);
  const label=element('label','','Levels ');label.append(this.depth);this.trail=element('div','master-trail');this.toolbar.append(label,this.trail);
  const layout=element('div','method-layout');const aside=element('aside','method-list');this.search=element('input');this.search.placeholder='Find a method';this.search.setAttribute('aria-label','Find a method');this.list=element('div');this.search.oninput=()=>this.drawList();aside.append(this.search,this.list);
  const main=element('div','method-main');const controls=element('div','method-controls');this.info=element('span');const fit=element('button','button','Fit');fit.onclick=()=>this.graph.fit();const minus=element('button','button','−'),plus=element('button','button','+');minus.onclick=()=>this.graph.zoom(-.15);plus.onclick=()=>this.graph.zoom(.15);controls.append(this.info,minus,fit,plus);
  const area=element('div','graph-area method-canvas');const ns='http://www.w3.org/2000/svg';this.svg=document.createElementNS(ns,'svg');this.svg.setAttribute('aria-label','Method relationships graph');this.svg.innerHTML='<defs><marker id="method-arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse"><path d="M0 0 L10 5 L0 10z" fill="#91a4b9"/></marker></defs><g id="graph-layer"></g>';area.append(this.svg);this.details=element('div','method-details');main.append(controls,area,this.details);layout.append(aside,main);this.dialog.append(header,this.toolbar,layout);document.body.append(this.dialog);
  this.graph=new FileGraph(this.svg,n=>this.select(n),n=>this.explore(n));this.graph.arrowId='method-arrow';
  this.dialog.addEventListener('close',()=>{this.ticket++;this.graph.data=null;});
 }
 async open(node){this.source=this.context().source;this.filters=this.context().filters;this.classNode=node;this.master=null;this.steps=[];this.cursor=-1;this.methods=[];this.items=[];this.search.value='';this.title.textContent=`Methods · ${node.name}`;this.list.replaceChildren(element('p','','Loading methods…'));this.details.replaceChildren();this.graph.clear();if(!this.dialog.open)this.dialog.showModal();
  const ticket=++this.ticket;
  try{
   // This request supplies the full class list; no children pagination can hide methods.
   const data=await api(`/api/explore/${this.source}/network?${new URLSearchParams({...this.filters,view:'methods',class_key:node.key,depth:1})}`);
   if(ticket!==this.ticket)return;this.methods=data.class_methods||[];this.items=this.methods;this.drawList();this.info.textContent=`${this.methods.length} methods in ${node.name}`;
   this.details.textContent=this.methods.length?'Choose a method to explore its relationships.':'No indexed methods in this class.';
  }catch(e){this.list.textContent=e.message;}
 }
 drawList(){this.list.replaceChildren();if(this.items!==this.methods){const back=element('button','button','Class methods');back.onclick=()=>{this.items=this.methods;this.search.value='';this.drawList();};this.list.append(back);}
 const q=this.search.value.toLowerCase();for(const n of this.items.filter(n=>(n.name+' '+n.path+' '+(n.class_name||n.parent_name||'')).toLowerCase().includes(q))){const b=element('button','component-choice'+(n.key===this.master?' active':''),(n.display_name||n.name)+' · '+(n.path||''));b.onclick=()=>this.load(n.key);this.list.append(b);}}
 async load(key,record=true){if(!key)return;const ticket=++this.ticket;this.info.textContent='Loading method graph…';try{const data=await api(`/api/explore/${this.source}/network?${new URLSearchParams({...this.filters,view:'methods',class_key:this.classNode.key,key,depth:this.depth.value})}`);if(ticket!==this.ticket)return;this.master=key;this.data=data;
 if(record){this.steps=this.steps.slice(0,this.cursor+1);this.steps.push(data.core);this.cursor=this.steps.length-1;}this.drawTrail();data.layoutKey=JSON.stringify([this.source,'method-dialog',key,this.depth.value,this.filters]);this.graph.render(data);this.info.textContent=`${data.visible_files} methods · ${data.hidden_files} hidden`;this.select(data.core);this.drawList();}catch(e){this.info.textContent=e.message;}}
 drawTrail(){this.trail.replaceChildren();const go=i=>{this.cursor=i;this.load(this.steps[i].key,false);};const back=element('button','button','Back'),next=element('button','button','Forward');back.disabled=this.cursor<=0;next.disabled=this.cursor>=this.steps.length-1;back.onclick=()=>go(this.cursor-1);next.onclick=()=>go(this.cursor+1);this.trail.append(back,next);this.steps.forEach((n,i)=>{const b=element('button','button'+(i===this.cursor?' primary':''),n.display_name||n.name);b.onclick=()=>go(i);this.trail.append(b);});}
 select(node){this.details.replaceChildren(element('strong','',node.display_name||node.name));if(node.category==='hidden'){const b=element('button','button','Explore hidden methods');b.onclick=()=>this.explore(node);this.details.append(b);return;}
 this.details.append(element('span','',`${node.class_name||node.parent_name||''} · ${node.path||''}`));const open=element('button','button','Open');open.onclick=()=>openCode(this.source,node);this.details.append(open);}
 explore(node){if(node.category==='hidden'){this.items=node.member_items||[];this.search.value='';this.drawList();this.info.textContent=`Choose one of ${node.hidden_count} hidden methods`;return;}return this.load(node.key);}
}
