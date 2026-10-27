import test from 'node:test';
import assert from 'node:assert/strict';
import {loadSession,saveSession} from '../graphviewer/static/session-store.js';
test('session round trip retains category, master, depth, filters and viewport',()=>{
 const data=new Map(),storage={getItem:k=>data.get(k),setItem:(k,v)=>data.set(k,v)};
 const session={source:'voiceflow',view:'classes',core:'class::A',depth:3,filters:{language:'python',tests:true},viewport:{scale:.75,pan:{x:101,y:-43}}};
 assert.equal(saveSession(storage,session),true);assert.deepEqual(loadSession(storage),session);
});
test('invalid sessions and unavailable storage safely fall back',()=>{
 for(const value of ['{bad','null','{}',JSON.stringify({source:'x',view:'methods',depth:2,core:null,viewport:{scale:1,pan:{x:0,y:0}}})])assert.equal(loadSession({getItem:()=>value}),null);
 assert.equal(saveSession({setItem:()=>{throw Error();}},{}),false);
});
test('restores a history cursor in the middle without losing the forward branch',()=>{
 let value;const storage={getItem:()=>value,setItem:(_,v)=>{value=v;}};
 const trail=[{key:'A',name:'Alpha',category:'classes'},{key:'B',name:'Beta',category:'classes'},{key:'C',name:'Gamma',category:'classes'}];
 const session={source:'demo',view:'classes',core:'B',depth:2,viewport:{scale:1,pan:{x:0,y:0}},trail,trailIndex:1,history:[{view:'files',core:'file.py'}]};
 saveSession(storage,session);const restored=loadSession(storage);
 assert.deepEqual(restored.trail,trail);assert.equal(restored.trailIndex,1);
 assert.equal(restored.trail[restored.trailIndex-1].key,'A');assert.equal(restored.trail[restored.trailIndex+1].key,'C');
 assert.deepEqual(restored.history,session.history);
});
test('invalid trail data is discarded while the valid session remains recoverable',()=>{
 const session={source:'demo',view:'classes',core:'B',depth:2,viewport:{scale:1,pan:{x:0,y:0}},trail:[{key:'A',name:'Alpha',category:'classes'}],trailIndex:10,history:'broken'};
 const restored=loadSession({getItem:()=>JSON.stringify(session)});
 assert.equal(restored.core,'B');assert.deepEqual(restored.trail,[]);assert.equal(restored.trailIndex,-1);assert.deepEqual(restored.history,[]);
});
