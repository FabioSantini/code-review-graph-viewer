from graphviewer.index import GraphIndex
from graphviewer.projected_network import ProjectedNetwork

def sample():
    nodes=[dict(qualified_name=k,name=name,kind=kind,file_path=path,parent_name=parent,language=lang) for k,name,kind,path,parent,lang in [
      ('a.py','a.py','File','a.py',None,'python'),('b.js','b.js','File','b.js',None,'javascript'),
      ('A','A','Class','a.py',None,'python'),('B','B','Class','b.js',None,'javascript'),
      ('A.run','run','Function','a.py','A','python'),('B.run','run','Function','b.js','B','javascript'),
      ('f','f','Function','a.py',None,'python'),('g','g','Function','b.js',None,'javascript')]]
    edges=[dict(source_qualified=a,target_qualified=b,kind=kind,target_resolution='direct') for a,b,kind in [
      ('A','A.run','CONTAINS'),('B','B.run','CONTAINS'),('A.run','B.run','CALLS'),('B','A','INHERITS'),('f','g','CALLS')]]
    return GraphIndex(nodes,edges)

def test_class_projection_preserves_member_dependencies_and_inheritance():
    net=ProjectedNetwork(sample(),'classes')
    assert set(net.nodes)=={'A','B'}
    assert {(e['source'],e['target']) for e in net.edges}=={('A','B'),('B','A')}
    assert net.graph('A')['visible_files']==2

def test_methods_keep_class_identity_and_standalone_functions_are_separate():
    methods=ProjectedNetwork(sample(),'methods')
    assert methods.nodes['A.run']['display_name']=='A.run'
    assert methods.nodes['B.run']['class_key']=='B'
    assert {(e['source'],e['target']) for e in methods.edges}=={('A.run','B.run')}
    functions=ProjectedNetwork(sample(),'functions')
    assert set(functions.nodes)=={'f','g'}
    assert len(functions.edges)==1

def test_group_views_aggregate_and_languages_keep_isolated_nodes():
    idx=sample()
    for view in ('folders','languages','architecture'):
        net=ProjectedNetwork(idx,view)
        assert sum(n['member_count'] for n in net.nodes.values())==2
    net=ProjectedNetwork(idx,'languages')
    assert len(net.graph('@languages:python')['nodes'])==2
    net=ProjectedNetwork(idx,'languages',relation='REFERENCES')
    assert len(net.graph('@languages:python')['nodes'])==2
    assert not net.edges

def test_empty_and_filtered_categories():
    assert not ProjectedNetwork(sample(),'classes',language='bash').nodes

def test_network_routes_and_class_method_list(graph,tmp_path):
    from fastapi.testclient import TestClient
    from graphviewer.app import create_app
    with TestClient(create_app({'demo':graph},sources_file=tmp_path/'sources.json')) as client:
        for view in ['files','classes','functions','folders','languages','architecture']:
            response=client.get(f'/api/explore/demo/network?view={view}&depth=1')
            assert response.status_code==200
            assert response.json()['core'] is not None
        result=client.get('/api/explore/demo/network',params={'view':'methods','class_key':'app.py::Engine'}).json()
        assert result['core'] is None
        assert [n['name'] for n in result['class_methods']]==['run']
        method=client.get('/api/explore/demo/network',params={'view':'methods','class_key':'app.py::Engine','key':'app.py::Engine.run'}).json()
        assert method['core']['class_name']=='Engine'
        assert client.get('/api/explore/demo/network?depth=11').status_code==422
        assert client.get('/api/explore/demo/network?key=absent').status_code==404
