"""File components and complete two-hop projections."""
from collections import Counter
from fastapi import HTTPException
from .explore import visible

class FileNetwork:
    def __init__(self, index, tests=False, resolved=True, relation='', language='', folder=''):
        self.nodes={n['key']:n for n in index.nodes.values() if n['kind']=='File' and visible(n,language,folder,tests)}
        by_path={n['file_path']:k for k,n in self.nodes.items()}
        counts=Counter()
        for e in index.edges:
            if e['kind']=='CONTAINS' or (relation and e['kind']!=relation):continue
            if resolved and e['kind']=='CALLS' and e.get('target_resolution')!='direct':continue
            a=index.nodes.get(e['source_qualified']);b=index.nodes.get(e['target_qualified'])
            if not a or not b or not visible(a,language,folder,tests) or not visible(b,language,folder,tests):continue
            s,t=by_path.get(a.get('file_path')),by_path.get(b.get('file_path'))
            if s and t and s!=t:counts[s,t]+=1
        self.finish(counts)

    def finish(self, counts):
        self.edges=[dict(source=s,target=t,kind='DEPENDENCY',count=c) for (s,t),c in counts.items()]
        self.adj={k:set() for k in self.nodes}
        for s,t in counts:self.adj[s].add(t);self.adj[t].add(s)
        unseen=set(self.nodes);self.groups=[]
        while unseen:
            seed=min(unseen);unseen.remove(seed);group={seed};stack=[seed]
            while stack:
                for n in self.adj[stack.pop()]:
                    if n in unseen:unseen.remove(n);group.add(n);stack.append(n)
            self.groups.append(group)
        self.groups.sort(key=lambda g:(-len(g),min(g)))

    def components(self):
        return [dict(id=min(g),master=min(g),files=len(g),name=self.nodes[min(g)]['path'],languages=sorted({self.nodes[k].get('language','') for k in g})) for g in self.groups]

    def graph(self, master, depth=2):
        if master not in self.nodes:raise HTTPException(404,'File not found in current scope')
        group=next(g for g in self.groups if master in g)
        distances={master:0}
        frontier={master}
        for level in range(1, depth+1):
            following=set()
            for node in frontier:following.update(self.adj[node])
            following-=distances.keys()
            distances.update({node:level for node in following})
            frontier=following
            if not frontier:break
        shown=set(distances)
        nodes=[dict(self.nodes[k],level=distances[k]) for k in sorted(shown)]
        edges=[e for e in self.edges if e['source'] in shown and e['target'] in shown]
        # Partition the hidden induced graph: every hidden file belongs to exactly one summary.
        unseen=group-shown
        summaries={}
        while unseen:
            seed=min(unseen);unseen.remove(seed);members={seed};pending=[seed]
            while pending:
                current=pending.pop()
                for neighbor in self.adj[current] & unseen:
                    unseen.remove(neighbor);members.add(neighbor);pending.append(neighbor)
            key='@hidden:'+seed
            nodes.append(dict(key=key,name='+'+str(len(members)),category='hidden',kind='Hidden',level=depth+1,
                              hidden_count=len(members),members=sorted(members),sample_paths=[self.nodes[k]['path'] for k in sorted(members)[:5]],member_items=[dict(key=k,name=self.nodes[k]['name'],path=self.nodes[k].get('path',''),category=self.nodes[k]['category'],parent_name=self.nodes[k].get('parent_name'),class_name=self.nodes[k].get('class_name'),class_key=self.nodes[k].get('class_key'),display_name=self.nodes[k].get('display_name')) for k in sorted(members)]))
            for member in members:summaries[member]=key
        boundary=Counter()
        for edge in self.edges:
            a,b=edge['source'],edge['target']
            if a in shown and b in summaries:boundary[a,summaries[b]]+=edge['count']
            elif a in summaries and b in shown:boundary[summaries[a],b]+=edge['count']
        edges.extend(dict(source=a,target=b,kind='HIDDEN',count=count) for (a,b),count in boundary.items())
        return dict(core=self.nodes[master],nodes=nodes,edges=edges,layered=True,component=min(group),component_size=len(group),visible_files=len(shown),hidden_files=len(group-shown),depth=depth,level1=sum(v==1 for v in distances.values()),level2=sum(v==2 for v in distances.values()))
