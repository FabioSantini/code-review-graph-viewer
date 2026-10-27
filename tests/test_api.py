from fastapi.testclient import TestClient

from graphviewer.app import create_app




def test_project_overview(graph):
    with TestClient(create_app({"demo": graph})) as client:
        assert client.get("/api/projects").json()[0]["available"] is True
        result = client.get("/api/projects/demo/overview").json()
        assert result["nodes"] == 4
        assert result["edges"] == 4


def test_drill_down_uses_containment(graph):
    with TestClient(create_app({"demo": graph})) as client:
        file_children = client.get("/api/projects/demo/nodes/1/children").json()
        assert {n["name"] for n in file_children} == {"Engine", "main"}
        class_children = client.get("/api/projects/demo/nodes/2/children").json()
        assert [n["name"] for n in class_children] == ["run"]


def test_core_neighborhood_directions(graph):
    with TestClient(create_app({"demo": graph})) as client:
        result = client.get("/api/projects/demo/nodes/3/neighbors?direction=in").json()
        assert result["core"]["name"] == "run"
        assert [n["name"] for n in result["nodes"]] == ["main"]
        assert result["edges"][0]["kind"] == "CALLS"
        assert client.get("/api/projects/demo/nodes/3/neighbors?direction=out").json()["nodes"] == []


def test_missing_database_is_not_created(tmp_path):
    missing = tmp_path / "missing.db"
    with TestClient(create_app({"demo": missing})) as client:
        assert client.get("/api/projects/demo/overview").status_code == 503
        assert client.get("/api/projects/unknown/overview").status_code == 404
    assert not missing.exists()


def test_missing_node_and_bounded_query(graph):
    with TestClient(create_app({"demo": graph})) as client:
        assert client.get("/api/projects/demo/nodes/999/children").status_code == 404
        assert client.get("/api/projects/demo/nodes/1/neighbors?limit=1001").status_code == 422
        assert client.get("/api/projects/demo/nodes/1/neighbors?direction=other").status_code == 422


def test_queries_do_not_modify_database(graph):
    before = graph.read_bytes()
    with TestClient(create_app({"demo": graph})) as client:
        client.get("/api/projects/demo/overview")
        client.get("/api/projects/demo/nodes/3/neighbors")
    assert graph.read_bytes() == before
