"""Shared graph projection for symbols, directories, languages and areas."""
from collections import Counter
from .file_network import FileNetwork
from .explore import visible, group_key, group_node

class ProjectedNetwork(FileNetwork):
    def __init__(self,index,view,tests=False,resolved=True,relation='',language='',folder=''):
        self.view=view
        allowed={k:n for k,n in index.nodes.items() if visible(n,language,folder,tests)}
        grouped=view in ('folders','languages','architecture')
        owners={}
        if grouped:
            counts=Counter(group_key(n,view) for n in allowed.values() if n['kind']=='File')
            self.nodes={('@'+view+':'+key):group_node(key,view,count) for key,count in counts.items()}
            for k,n in allowed.items():
                candidate='@'+view+':'+group_key(n,view)
                if candidate in self.nodes:owners[k]=candidate
            for key,node in self.nodes.items():
                node['symbol_count']=sum(owner==key for owner in owners.values())
                node['language']=key.split(':',1)[1] if view=='languages' else ''
        else:
            self.nodes={k:dict(n) for k,n in allowed.items() if n['category']==view}
            for k in allowed:
                owner=index.owner(k,'classes') if view=='classes' else k
                if owner in self.nodes:owners[k]=owner
            if view=='methods':
                for k,n in self.nodes.items():
                    owner=index.owner(k,'classes');n['class_key']=owner
                    n['class_name']=index.nodes.get(owner,{}).get('name',n.get('parent_name',''))
                    n['display_name']=n['class_name']+'.'+n['name']
        counts=Counter()
        for edge in index.edges:
            if edge['kind']=='CONTAINS' or (relation and relation!=edge['kind']):continue
            if resolved and edge['kind']=='CALLS' and edge.get('target_resolution')!='direct':continue
            a,b=owners.get(edge['source_qualified']),owners.get(edge['target_qualified'])
            if a and b and a!=b:counts[a,b]+=1
        self.finish(counts)

    def components(self):
        values=super().components()
        for value,group in zip(values,self.groups):
            value['name']=self.nodes[value['master']]['name']
            value['path']=self.nodes[value['master']].get('path','')
            value['category']=self.view
        return values

    def graph(self,master,depth=2):
        result=super().graph(master,depth)
        result['view']=self.view
        if self.view=='languages':
            result.update(nodes=[dict(n,level=0 if k==master else 1) for k,n in self.nodes.items()],edges=self.edges,
                          visible_files=len(self.nodes),hidden_files=0,component_size=len(self.nodes))
        return result
