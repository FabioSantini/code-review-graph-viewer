import { loadSession, saveSession } from './session-store.js?v=history-1';
import { api, labels, element } from './api.js';
import { Graph } from './graph.js';
import { FileGraph } from './file-graph.js?v=session-1';
import { MethodExplorer } from './method-explorer.js?v=2';
import { inspect } from './inspector.js';
import { Sources } from './sources.js';
import { Browser } from './browser.js?v=all-views-1';
import { openCode } from './code-view.js';
const state={source:'',view:'architecture',core:null,history:[],sequence:0,sources:[]};
let restoredSession=loadSession(localStorage),sessionContext=null,sessionTimer;
function persistSession(){if(!sessionContext||!graph.data)return;saveSession(localStorage,{...sessionContext,viewport:{scale:graph.scale,pan:{...graph.pan}}});}
function scheduleSession(){clearTimeout(sessionTimer);sessionTimer=setTimeout(persistSession,120);}
window.addEventListener('pagehide',persistSession);
document.addEventListener('visibilitychange',()=>{if(document.hidden)persistSession();});

let graph=new Graph(document.querySelector('#graph'),select,explore),fileMode=false,fileTrail=[],trailIndex=-1;
const browser=new Browser(()=>({...state,filters:filters(),viewLabel:labels[state.view]}),choose);
const sources=new Sources(reloadSources);
const methods=new MethodExplorer(()=>({source:state.source,filters:filters()}));
const navigation=element('section','component-navigation');navigation.hidden=true;document.querySelector('.inspector').prepend(navigation);
const depthSelect=document.querySelector('#graph-depth');
try{const saved=Number(localStorage.getItem('graphviewer-depth'));if(saved>=1&&saved<=10)depthSelect.value=String(saved);}catch{}
depthSelect.onchange=()=>{try{localStorage.setItem('graphviewer-depth',depthSelect.value);}catch{}return render();};
const trail=element('div','master-trail');trail.hidden=true;document.querySelector('.graph-toolbar').after(trail);
function filters(){return {language:document.querySelector('#language').value,folder:document.querySelector('#folder').value.trim(),tests:document.querySelector('#include-tests').checked,resolved_only:document.querySelector('#resolved').checked,relation:document.querySelector('#relation').value};}
function message(text,error=false){const n=document.querySelector('#graph-message');n.textContent=text;n.hidden=!text;n.classList.toggle('error',error);}
function notice(text=''){const n=document.querySelector('#notice');n.textContent=text;n.hidden=!text;}
function hiddenItems(node){return node.member_items||node.members.map(key=>{const path=key.replaceAll('\\','/');return {key,path,name:path.split('/').at(-1),category:'files'};});}
function openHidden(node){return browser.openItems(hiddenItems(node),`${node.hidden_count} hidden elements`);}
function select(node){if(node.category==='hidden'){
 const target=document.querySelector('#node-info');target.replaceChildren(element('span','kind-pill','Hidden group'),element('h3','',`${node.hidden_count} elements`),element('p','','Each element belongs to this group once. Double-click to choose a new Master.'));
 const b=element('button','button primary','Explore elements');b.onclick=()=>openHidden(node);target.append(b);return;
}inspect(node,state.graph,choose,n=>n.category==='classes'?methods.open(n):browser.open(n),n=>openCode(state.source,n));}
async function explore(node,event){if(node.category==='hidden')return openHidden(node);if(node.category==='classes'&&event?.altKey)return methods.open(node);return choose(node);}
async function choose(node){if(node.category==='methods'){return methods.open({key:node.class_key,name:node.parent_name||node.class_name});}state.history.push({view:state.view,core:state.core});state.view=node.category==='tests'?'functions':node.category;state.core=node.key;await render();}
function showTrail(){trail.replaceChildren();trail.hidden=!fileMode;if(!fileMode)return;
 const go=async i=>{trailIndex=i;state.core=fileTrail[i].key;state.view=fileTrail[i].category;await render();};
 const back=element('button','button','Back'),forward=element('button','button','Forward');back.disabled=trailIndex<=0;forward.disabled=trailIndex>=fileTrail.length-1;back.onclick=()=>go(trailIndex-1);forward.onclick=()=>go(trailIndex+1);trail.append(back,forward);
 fileTrail.forEach((n,i)=>{const b=element('button','button'+(i===trailIndex?' primary':''),n.name);b.onclick=()=>go(i);trail.append(b);});
}
function showComponents(data){
 const grouped=['folders','languages','architecture'].includes(state.view);
 navigation.replaceChildren(element('h3','',grouped?{folders:'Project directories',languages:'Languages',architecture:'Project areas'}[state.view]:labels[state.view]+' components'));
 const search=element('input');search.placeholder='Search navigation';search.setAttribute('aria-label','Search navigation');navigation.append(search);
 const list=element('div','component-list');navigation.append(list);
 if(state.view==='folders'){
   const root={children:new Map()};
   for(const n of data.navigation||[]){let parent=root;for(const part of n.name.replaceAll('\\','/').split('/')){if(!parent.children.has(part))parent.children.set(part,{children:new Map()});parent=parent.children.get(part);}parent.node=n;}
   function draw(parent,target){for(const [name,branch] of [...parent.children].sort(([a],[b])=>a.localeCompare(b))){
    const box=branch.children.size?element('details','folder-branch'):element('div','folder-branch');if(branch.children.size){box.open=true;box.append(element('summary','',name));}
    if(branch.node){const n=branch.node,b=element('button','component-choice'+(n.key===state.core?' active':''),`${name} · ${n.member_count} files`);b.onclick=()=>choose(n);b.title=n.path;box.append(b);}
    draw(branch,box);target.append(box);
   }}draw(root,list);
 }else if(grouped){for(const n of data.navigation||[]){const b=element('button','component-choice'+(n.key===state.core?' active':''),`${n.name} · ${n.member_count} files · ${n.symbol_count} symbols`);b.onclick=()=>choose(n);list.append(b);}}
 else data.components.forEach((c,i)=>{const b=element('button','component-choice'+(c.id===data.component?' active':''),`${i+1}. ${c.files} ${labels[state.view].toLowerCase()} · ${c.name}${['classes','functions'].includes(state.view)?' · '+(c.path||''):''}`);b.title=c.path||c.name;b.onclick=()=>choose({key:c.master,category:state.view,name:c.name});list.append(b);});
 search.oninput=()=>{const q=search.value.toLowerCase();for(const b of list.querySelectorAll('.component-choice'))b.hidden=!(b.textContent+' '+b.title).toLowerCase().includes(q);};
}
function overview(data){const items=data.items.slice(0,12),source=state.sources.find(s=>s.id===state.source);return {core:{key:'@root',name:source.name,category:state.view,overview:true},nodes:items,outgoing:items.filter((_,i)=>i%2===0),incoming:items.filter((_,i)=>i%2),edges:items.map(n=>({source:'@root',target:n.key,kind:'CONTAINS',count:1})),overview:true,total_neighbors:data.total};}
function updateLanguages(values){const s=document.querySelector('#language'),current=s.value;s.replaceChildren(element('option','','All languages'));s.firstChild.value='';for(const v of values||[]){const o=element('option','',v);o.value=v;s.append(o);}s.value=current;}
async function render(preserveViewport=false){const previousViewport=preserveViewport&&graph.data?{scale:graph.scale,pan:{...graph.pan}}:null;const sequence=++state.sequence;notice();document.querySelector('#view-title').textContent=labels[state.view];document.querySelector('#view-description').textContent=state.view==='classes'?'Double-click: Master · Alt + double-click: methods explorer':'Double-click to change Master. Depth controls exploration, not hierarchy.';document.querySelector('#breadcrumb').textContent=`${state.sources.find(s=>s.id===state.source)?.name||''} / ${labels[state.view]}`;for(const b of document.querySelectorAll('#views button'))b.classList.toggle('active',b.dataset.view===state.view);document.querySelector('#back').disabled=!state.history.length;
 if(!state.source){graph.clear();message('Add a graph source to start exploring.');return;}
 message('Loading graph…');const query=new URLSearchParams({...filters(),depth:depthSelect.value,view:state.view,limit:state.core?16:50});if(state.core)query.set('key',state.core);
 try{const started=performance.now(),isFiles=true;const data=await api(`/api/explore/${state.source}/network?${query}`);if(sequence!==state.sequence)return;
 if(isFiles!==fileMode){graph.events.abort();graph.resizeObserver.disconnect();graph.clear();graph=isFiles?new FileGraph(document.querySelector('#graph'),select,explore):new Graph(document.querySelector('#graph'),select,explore);fileMode=isFiles;}navigation.hidden=!isFiles;document.querySelector('#depth-control').hidden=!isFiles;
 graph.onSaveError=()=>notice('Unable to save node positions in browser storage.');
 updateLanguages(data.languages);
 if(isFiles){showComponents(data);if(!data.core){graph.clear();document.querySelector('#node-info').replaceChildren(element('p','','No indexed elements in this category and scope.'));showTrail();message('No elements in this scope.');return;}state.core=data.core.key;if(fileTrail[trailIndex]?.key!==state.core||fileTrail[trailIndex]?.category!==state.view){fileTrail=fileTrail.slice(0,trailIndex+1);fileTrail.push(data.core);trailIndex=fileTrail.length-1;}}
 showTrail();state.graph=isFiles?data:state.core?data:overview(data);state.graph.layoutKey=JSON.stringify([state.source,state.view,state.core,filters(),fileMode?depthSelect.value:null,'network-v3']);const t=performance.now();graph.onViewportChange=null;graph.render(state.graph);
 if(previousViewport){graph.scale=previousViewport.scale;graph.pan=previousViewport.pan;graph.transform();}
 if(restoredSession&&restoredSession.source===state.source&&restoredSession.view===state.view&&restoredSession.core===state.core){graph.scale=restoredSession.viewport.scale;graph.pan={...restoredSession.viewport.pan};graph.transform();}
 restoredSession=null;sessionContext={source:state.source,view:state.view,core:state.core,depth:Number(depthSelect.value),filters:filters(),trail:fileTrail.map(n=>({key:n.key,name:n.name,category:n.category})),trailIndex,history:state.history.map(n=>({...n}))};graph.onViewportChange=scheduleSession;persistSession();
 select(state.graph.core);message('');const ms=performance.now()-t;
 document.querySelector('#core-label').textContent=isFiles?`Master: ${data.core.name}`:state.core?data.core.name:'Project overview';
 document.querySelector('#graph-count').textContent=isFiles?`${data.visible_files} ${labels[state.view].toLowerCase()} · ${data.hidden_files} hidden · ${data.edges.length} links · render ${ms.toFixed(0)} ms · total ${(performance.now()-started).toFixed(0)} ms`:`${graph.visibleCount} of ${data.total_neighbors??data.total??data.nodes?.length} connected elements`;
 notice(data.notice||(data.partial?'Partial MCP catalog.':''));document.querySelector('#source-status').textContent='Graph ready';document.querySelector('#source-status').className='status ready';
 }catch(e){if(restoredSession&&state.core){restoredSession=null;state.core=null;return render();}message(e.message,true);}}
async function reloadSources(preferred){state.sources=await sources.reload();const previous=preferred||state.source||restoredSession?.source||localStorage.getItem('graphviewer-source');state.source=state.sources.some(s=>s.id===previous)?previous:state.sources[0]?.id||'';const s=document.querySelector('#source-select');s.replaceChildren();for(const item of state.sources){const o=element('option','',item.name);o.value=item.id;s.append(o);}s.value=state.source;state.core=null;state.history=[];fileTrail=[];trailIndex=-1;
 if(restoredSession?.source===state.source){
  state.view=restoredSession.view;state.core=restoredSession.core;depthSelect.value=String(restoredSession.depth);
  fileTrail=restoredSession.trail||[];trailIndex=restoredSession.trailIndex??-1;state.history=restoredSession.history||[];
  const f=restoredSession.filters||{};
  const lang=document.querySelector('#language');if(f.language){const o=element('option','',f.language);o.value=f.language;lang.append(o);}lang.value=f.language||'';
  document.querySelector('#folder').value=f.folder||'';
  document.querySelector('#relation').value=f.relation||'';
  document.querySelector('#include-tests').checked=!!f.tests;
  document.querySelector('#resolved').checked=f.resolved_only!==false;
 }else restoredSession=null;
 await render();}
document.querySelector('#source-select').onchange=async e=>{state.source=e.target.value;localStorage.setItem('graphviewer-source',state.source);state.core=null;state.history=[];fileTrail=[];trailIndex=-1;document.querySelector('#language').value='';document.querySelector('#folder').value='';await render();};
for(const b of document.querySelectorAll('#views button'))b.onclick=async()=>{state.history.push({view:state.view,core:state.core});state.view=b.dataset.view;state.core=null;await render();};
document.querySelector('#back').onclick=async()=>{const n=state.history.pop();if(n){state.view=n.view;state.core=n.core;await render();}};
document.querySelector('#home').onclick=async()=>{state.core=null;await render();};
document.querySelector('#browse').onclick=()=>browser.open();
document.querySelector('#refresh').onclick=async()=>{if(!state.source)return;try{await api(`/api/sources/${state.source}/refresh`,{method:'POST'});await render();}catch(e){message(e.message,true);}};
document.querySelector('#apply-filters').onclick=()=>{state.core=null;fileTrail=[];trailIndex=-1;return render();};
document.querySelector('#zoom-in').onclick=()=>graph.zoom(.15);document.querySelector('#zoom-out').onclick=()=>graph.zoom(-.15);document.querySelector('#zoom-reset').onclick=()=>graph.fit();
for(const b of document.querySelectorAll('.close-dialog'))b.onclick=()=>b.closest('dialog').close();
reloadSources().catch(e=>message(e.message,true));


// Poll only a small database/WAL signature; rebuild the graph only after it changes.
const liveLabel=element('label','live-toggle');const liveToggle=element('input');liveToggle.type='checkbox';liveToggle.checked=true;liveToggle.setAttribute('aria-label','Live database updates');liveLabel.append(liveToggle,document.createTextNode(' Live'));
document.querySelector('#refresh').before(liveLabel);
let liveRevision=null,liveSource='',liveBusy=false;
setInterval(async()=>{
 if(liveBusy||!liveToggle.checked||!state.source||document.hidden||graph.drag||document.querySelector('dialog[open]'))return;
 liveBusy=true;const source=state.source;
 try{
  const revision=await api(`/api/sources/${source}/revision`);
  if(source!==state.source)return;
  if(liveSource!==source){liveSource=source;liveRevision=null;}
  if(!revision.supported)return;
  if(liveRevision!==null&&revision.revision!==liveRevision){
   try{await render(true);}catch{}
  }
  liveRevision=revision.revision;
 }catch{}finally{liveBusy=false;}
},3000);
