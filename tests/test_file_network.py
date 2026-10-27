from graphviewer.file_network import FileNetwork
from graphviewer.index import GraphIndex

def test_two_levels_cycles_and_hidden_frontier():
    nodes=[dict(qualified_name=k,kind='File',name=k,file_path=k) for k in 'ABCDEFX']
    edges=[dict(source_qualified=a,target_qualified=b,kind='IMPORTS_FROM') for a,b in [('A','B'),('B','C'),('C','A'),('C','D'),('D','E'),('E','F')]]
    network=FileNetwork(GraphIndex(nodes,edges))
    assert sorted(c['files'] for c in network.components())==[1,6]
    result=network.graph('A')
    assert result['visible_files']==4
    assert result['hidden_files']==2
    assert {n['key'] for n in result['nodes'] if n['category']!='hidden'}==set('ABCD')
    assert [n['hidden_count'] for n in result['nodes'] if n['category']=='hidden']==[2]
    assert len({n['key'] for n in result['nodes']})==len(result['nodes'])
    assert network.graph('D')['visible_files']==6

def test_hidden_groups_are_disjoint_and_preserve_all_boundary_directions():
    nodes=[dict(qualified_name=k,kind='File',name=k,file_path=k) for k in 'ABCDEFG']
    pairs=[('A','B'),('A','C'),('B','D'),('C','E'),('D','F'),('F','E'),('F','G'),('E','B')]
    edges=[dict(source_qualified=a,target_qualified=b,kind='IMPORTS_FROM') for a,b in pairs]
    result=FileNetwork(GraphIndex(nodes,edges)).graph('A')
    hidden=[n for n in result['nodes'] if n['category']=='hidden']
    assert len(hidden)==1
    assert hidden[0]['hidden_count']==2
    assert set(hidden[0]['members'])=={'F','G'}
    assert sum(n['hidden_count'] for n in hidden)==result['hidden_files']
    summary=hidden[0]['key']
    boundary={(e['source'],e['target']) for e in result['edges'] if e['kind']=='HIDDEN'}
    assert boundary=={('D',summary),(summary,'E')}
    assert ('E','B') in {(e['source'],e['target']) for e in result['edges']}

def test_selectable_depth_and_summary_totals():
    nodes=[dict(qualified_name=k,kind='File',name=k,file_path=k) for k in 'ABCDE']
    edges=[dict(source_qualified=a,target_qualified=b,kind='IMPORTS_FROM') for a,b in zip('ABCD','BCDE')]
    network=FileNetwork(GraphIndex(nodes,edges))
    for depth,expected in [(1,2),(2,3),(3,4),(4,5),(10,5)]:
        result=network.graph('A',depth)
        assert result['visible_files']==expected
        assert sum(n['hidden_count'] for n in result['nodes'] if n['category']=='hidden')==5-expected
        assert all(n['level']<=depth for n in result['nodes'] if n['category']!='hidden')
