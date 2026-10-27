import asyncio

from graphviewer.index import GraphIndex
from graphviewer.remote import RemoteGraphs


def test_parent_name_classifies_remote_methods():
    nodes = [{"qualified_name": "x.py::C", "name": "C", "kind": "Class", "file_path": "x.py"},
             {"qualified_name": "x.py::C.run", "name": "run", "kind": "Function", "file_path": "x.py", "parent_name": "C"}]
    index = GraphIndex(nodes, [])
    assert index.nodes["x.py::C.run"]["category"] == "methods"


def test_remote_children_are_remembered_and_paginated():
    class Pool:
        async def call(self, source, name, args):
            return {"results": [{"qualified_name": f"x.py::C.m{i}", "name": f"m{i}", "kind": "Function", "file_path": "x.py"} for i in range(70)], "result_count": 70}

    async def scenario():
        remote = RemoteGraphs(Pool())
        source = {"id": "test"}
        remote.cache["test"] = GraphIndex([{"qualified_name": "x.py::C", "name": "C", "kind": "Class", "file_path": "x.py"}], [])
        result = await remote.children(source, "x.py::C", 50, 50)
        assert len(result["items"]) == 20
        assert result["items"][0]["name"] == "m50"
        index = await remote.catalog_index(source)
        assert index.nodes["x.py::C.m50"]["category"] == "methods"
    asyncio.run(scenario())


def test_remote_neighbors_keep_methods_and_apply_filters():
    class Pool:
        async def call(self, source, name, args):
            return {"results": [{"qualified_name": "x.py::C.run", "name": "run", "kind": "Function"},
                                {"qualified_name": "test.py::test_a", "name": "test_a", "kind": "Test", "is_test": True, "language": "python"}], "edges": []}

    async def scenario():
        remote = RemoteGraphs(Pool())
        source = {"id": "test"}
        index = GraphIndex([{"qualified_name": "x.py::C", "name": "C", "kind": "Class", "file_path": "x.py"},
                            {"qualified_name": "x.py::C.run", "name": "run", "kind": "Function", "file_path": "x.py", "parent_name": "C", "language": "python"}], [])
        remote.cache["test"] = index
        core = {"key": "main.py::main", "name": "main", "kind": "Function"}
        result = await remote.graph(source, core, True, limit=1, language="python")
        assert len(result["nodes"]) == 1
        assert result["nodes"][0]["category"] == "methods"
        result = await remote.graph(source, core, True, language="javascript")
        assert result["nodes"] == []
    asyncio.run(scenario())
