from fastapi.testclient import TestClient

from graphviewer.app import create_app


def test_explorer_static_and_bootstrapped_sources(graph, tmp_path):
    with TestClient(create_app({"demo": graph}, sources_file=tmp_path / "sources.json")) as client:
        assert client.get("/").status_code == 200
        assert "GraphViewer" in client.get("/").text
        sources = client.get("/api/sources").json()
        assert len(sources) == 1
        assert sources[0]["name"] == "demo"


def test_sources_persist_and_validate(graph, tmp_path):
    config = tmp_path / "sources.json"
    payload = {"name": "Other", "transport": "http", "url": "http://127.0.0.1:9123/mcp"}
    with TestClient(create_app({"demo": graph}, sources_file=config)) as client:
        response = client.post("/api/sources", json=payload)
        assert response.status_code == 201
        identity = response.json()["id"]
        assert client.post("/api/sources", json={**payload, "url": "file:///etc/passwd"}).status_code == 422
        assert client.post("/api/sources", json=payload, headers={"origin": "https://evil.example"}).status_code == 403
    with TestClient(create_app({"demo": graph}, sources_file=config)) as client:
        assert any(source["id"] == identity for source in client.get("/api/sources").json())
        assert client.delete(f"/api/sources/{identity}").status_code == 204


def test_catalog_separates_class_methods(graph, tmp_path):
    with TestClient(create_app({"demo": graph}, sources_file=tmp_path / "sources.json")) as client:
        for view, expected in [("files", ["app.py"]), ("classes", ["Engine"]),
                               ("functions", ["main"]), ("methods", ["run"])]:
            result = client.get(f"/api/explore/demo/catalog?view={view}")
            assert result.status_code == 200, result.text
            assert [node["name"] for node in result.json()["items"]] == expected


def test_file_class_aggregation_and_drilldown(graph, tmp_path):
    with TestClient(create_app({"demo": graph}, sources_file=tmp_path / "sources.json")) as client:
        children = client.get("/api/explore/demo/children", params={"key": "app.py"}).json()
        assert {node["name"] for node in children["items"]} == {"Engine", "main"}
        children = client.get("/api/explore/demo/children", params={"key": "app.py::Engine"}).json()
        assert [node["category"] for node in children["items"]] == ["methods"]
        result = client.get("/api/explore/demo/graph", params={"view": "methods", "key": "app.py::Engine.run"}).json()
        assert result["core"]["name"] == "run"
        assert result["incoming"][0]["name"] == "main"
        assert not result["outgoing"]
        assert result["edges"][0]["target"] == "app.py::Engine.run"


def test_filters_and_local_connectivity(graph, tmp_path):
    with TestClient(create_app({"demo": graph}, sources_file=tmp_path / "sources.json")) as client:
        assert client.get("/api/explore/demo/catalog?view=classes&language=javascript").json()["total"] == 0
        assert client.get("/api/explore/demo/catalog?view=classes&q=Engine").json()["total"] == 1
        assert client.get("/api/explore/demo/catalog?view=classes&limit=5000").status_code == 422
        assert client.get("/api/explore/demo/graph?view=classes&key=missing").status_code == 404
