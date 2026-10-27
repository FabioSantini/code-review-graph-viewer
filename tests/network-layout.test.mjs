import test from 'node:test';
import assert from 'node:assert/strict';
import {networkPositions} from '../graphviewer/static/network-layout.js';
test('graph layout is deterministic, finite and independent of exploration levels',()=>{
 const nodes=Array.from({length:30},(_,i)=>({key:String(i),level:i%3}));
 const edges=nodes.slice(1).map((n,i)=>({source:String(i),target:n.key}));
 const a=networkPositions(nodes,edges,800,600),b=networkPositions(nodes.map(n=>({...n,level:0})),edges,800,600);
 assert.deepEqual(a,b);assert.equal(a.size,30);
 assert.ok([...a.values()].every(p=>Number.isFinite(p.x)&&Number.isFinite(p.y)));
 assert.ok(new Set([...a.values()].map(p=>p.x)).size>20);
});
