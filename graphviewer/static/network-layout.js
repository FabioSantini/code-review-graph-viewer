// Deterministic spring layout: levels control exploration, never node placement.
export function networkPositions(nodes, edges, width, height) {
 const count=nodes.length, index=new Map(nodes.map((n,i)=>[n.key,i]));
 const radius=Math.max(170,Math.sqrt(count)*44), golden=Math.PI*(3-Math.sqrt(5));
 const points=nodes.map((n,i)=>{const r=radius*Math.sqrt((i+.5)/Math.max(1,count)),a=i*golden;return {x:Math.cos(a)*r,y:Math.sin(a)*r};});
 const links=edges.map(e=>[index.get(e.source),index.get(e.target)]).filter(([a,b])=>a!==undefined&&b!==undefined);
 for(let iteration=0;iteration<160;iteration++){
  const force=points.map(p=>({x:-p.x*.008,y:-p.y*.008}));
  for(let i=0;i<count;i++)for(let j=i+1;j<count;j++){
   const a=points[i],b=points[j],dx=a.x-b.x,dy=a.y-b.y,dist2=Math.max(25,dx*dx+dy*dy),dist=Math.sqrt(dist2);
   const push=Math.min(18,2100/dist2),fx=dx/dist*push,fy=dy/dist*push;
   force[i].x+=fx;force[i].y+=fy;force[j].x-=fx;force[j].y-=fy;
   if(Math.abs(dx)<126&&Math.abs(dy)<38){
    const overlapX=126-Math.abs(dx),overlapY=38-Math.abs(dy);
    if(overlapX<overlapY*2){const f=(dx>=0?1:-1)*overlapX*.22;force[i].x+=f;force[j].x-=f;}
    else{const f=(dy>=0?1:-1)*overlapY*.35;force[i].y+=f;force[j].y-=f;}
   }
  }
  for(const [i,j]of links){const dx=points[j].x-points[i].x,dy=points[j].y-points[i].y,d=Math.max(1,Math.hypot(dx,dy)),pull=(d-155)*.012;
   force[i].x+=dx/d*pull;force[i].y+=dy/d*pull;force[j].x-=dx/d*pull;force[j].y-=dy/d*pull;}
  const step=1-iteration/200;
  points.forEach((p,i)=>{p.x+=Math.max(-22,Math.min(22,force[i].x))*step;p.y+=Math.max(-22,Math.min(22,force[i].y))*step;});
 }
 // Resolve remaining label collisions after the spring system settles.
 for(let pass=0;pass<90;pass++){
  let collisions=0;
  for(let i=0;i<count;i++)for(let j=i+1;j<count;j++){
   const dx=points[j].x-points[i].x,dy=points[j].y-points[i].y;
   if(Math.abs(dx)<124&&Math.abs(dy)<34){
    collisions++;
    if((124-Math.abs(dx))<(34-Math.abs(dy))*2){const shift=(124-Math.abs(dx)+.5)/2*(dx>=0?1:-1);points[i].x-=shift;points[j].x+=shift;}
    else {const shift=(34-Math.abs(dy)+.5)/2*(dy>=0?1:-1);points[i].y-=shift;points[j].y+=shift;}
   }
  }
  if(!collisions)break;
 }
 return new Map(nodes.map((n,i)=>[n.key,{x:points[i].x+width/2,y:points[i].y+height/2}]));
}
