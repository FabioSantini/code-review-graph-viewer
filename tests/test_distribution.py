from fastapi.testclient import TestClient
from graphviewer.app import create_app
from graphviewer.demo import create_demo
from graphviewer.index import IndexCache

def test_fresh_install_and_packaged_static(tmp_path,monkeypatch):
    monkeypatch.chdir(tmp_path)
    with TestClient(create_app(sources_file=tmp_path/'sources.json')) as client:
        assert client.get('/api/sources').json()==[]
        assert client.get('/').status_code==200
        assert 'Live database updates' in client.get('/static/app.js?v=test').text
        assert client.get('/static/method-explorer.js').status_code==200

def test_demo_code_methods_and_read_only_live_revision(tmp_path):
    root=create_demo(tmp_path/'demo')
    path=root/'.code-review-graph/graph.db'
    before=path.read_bytes()
    with TestClient(create_app({'demo':path},sources_file=tmp_path/'sources.json')) as client:
        for view in ['files','classes','functions','folders','languages','architecture']:
            r=client.get('/api/explore/demo/network',params={'view':view,'depth':2})
            assert r.status_code==200
            assert r.json()['core'] is not None
        index=IndexCache().get({'database_path':str(path),'repo_root':str(root)})
        cls=next(n for n in index.nodes.values() if n['name']=='OrderService')
        methods=client.get('/api/explore/demo/network',params={'view':'methods','class_key':cls['key']}).json()['class_methods']
        place=next(n for n in methods if n['name']=='place')
        graph=client.get('/api/explore/demo/network',params={'view':'methods','key':place['key'],'depth':2}).json()
        assert any(n.get('class_name')=='OrderRepository' for n in graph['nodes'])
        assert 'def place' in client.get('/api/explore/demo/code',params={'key':place['key']}).json()['code']
        first=client.get('/api/sources/demo/revision').json()
        assert first['supported'] and first['available']
        assert first==client.get('/api/sources/demo/revision').json()
        assert path.read_bytes()==before
        import sqlite3
        with sqlite3.connect(path) as db:
            db.execute("INSERT INTO nodes(kind,name,qualified_name,file_path,language) VALUES('File','extra.py','extra.py','extra.py','python')")
        assert client.get('/api/sources/demo/revision').json()['revision']!=first['revision']
        assert any(c['master']=='extra.py' for c in client.get('/api/explore/demo/network?view=files').json()['components'])
