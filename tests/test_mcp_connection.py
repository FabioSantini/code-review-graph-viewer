import sys

from fastapi.testclient import TestClient

from graphviewer.app import create_app


def test_stdio_connection_uses_real_mcp_protocol(graph, tmp_path):
    server = tmp_path / "fake_graph_server.py"
    server.write_text('''from mcp.server.fastmcp import FastMCP
mcp = FastMCP("Test code graph")
@mcp.tool()
def list_graph_stats_tool(repo_root: str = "") -> dict:
    return {"status": "ok", "total_nodes": 4, "repo": repo_root}
mcp.run(transport="stdio")
''', encoding="utf-8")
    payload = {"name": "MCP test", "transport": "stdio", "command": sys.executable,
               "args": [str(server)], "repo_root": str(tmp_path)}
    with TestClient(create_app({"demo": graph}, sources_file=tmp_path / "sources.json")) as client:
        source = client.post("/api/sources", json=payload).json()
        response = client.post(f"/api/sources/{source['id']}/connect")
        assert response.status_code == 200, response.text
        assert response.json()["mode"] == "mcp"
        assert response.json()["statistics"]["total_nodes"] == 4
        assert "list_graph_stats_tool" in response.json()["tools"]


def test_class_dependency_aggregates_member_calls(graph, tmp_path):
    import sqlite3

    with sqlite3.connect(graph) as db:
        db.executescript("""
            INSERT INTO nodes VALUES (5,'Class','Other','other.py::Other','other.py',NULL,'python',1,10);
            INSERT INTO nodes VALUES (6,'Function','work','other.py::Other.work','other.py','Other','python',2,5);
            INSERT INTO edges VALUES (5,'CONTAINS','other.py::Other','other.py::Other.work','direct');
            INSERT INTO edges VALUES (6,'CALLS','app.py::Engine.run','other.py::Other.work','direct');
            INSERT INTO edges VALUES (7,'CALLS','other.py::Other.work','app.py::Engine.run','unresolved');
        """)
    with TestClient(create_app({"demo": graph}, sources_file=tmp_path / "sources.json")) as client:
        query = {"view": "classes", "key": "app.py::Engine"}
        result = client.get("/api/explore/demo/graph", params=query).json()
        assert [node["name"] for node in result["outgoing"]] == ["Other"]
        assert not result["incoming"]
        result = client.get("/api/explore/demo/graph", params={**query, "resolved_only": False}).json()
        assert [node["name"] for node in result["incoming"]] == ["Other"]


def test_index_refreshes_after_database_change(graph, tmp_path):
    import sqlite3

    with TestClient(create_app({"demo": graph}, sources_file=tmp_path / "sources.json")) as client:
        assert client.get("/api/explore/demo/catalog?view=classes").json()["total"] == 1
        with sqlite3.connect(graph) as db:
            db.execute("INSERT INTO nodes VALUES (5,'Class','New','app.py::New','app.py',NULL,'python',30,40)")
        result = client.get("/api/explore/demo/catalog?view=classes").json()
        assert result["total"] == 2
