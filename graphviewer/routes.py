"""HTTP routes for code graph exploration."""
from typing import Literal

from fastapi import Query

from . import store


def register_project_routes(app, database, registry):
    @app.get("/api/projects")
    def list_projects():
        return [{"id": name, "available": path.is_file()} for name, path in registry.items()]

    @app.get("/api/projects/{project}/overview")
    def project_overview(project: str):
        with database(project) as db:
            return store.overview(db)



def register_node_routes(app, database):
    @app.get("/api/projects/{project}/nodes")
    def nodes(project: str, kind: Literal["File", "Class", "Function", "Test"] = "File",
              limit: int = Query(50, ge=1, le=200), offset: int = Query(0, ge=0)):
        with database(project) as db:
            rows = db.execute("SELECT * FROM nodes WHERE kind=? ORDER BY name,id LIMIT ? OFFSET ?",
                              (kind, limit, offset))
            return [dict(row) for row in rows]

    @app.get("/api/projects/{project}/nodes/{node_id}/children")
    def node_children(project: str, node_id: int):
        with database(project) as db:
            return store.children(db, store.get_node(db, node_id))

    @app.get("/api/projects/{project}/nodes/{node_id}/neighbors")
    def node_neighbors(project: str, node_id: int,
                       direction: Literal["in", "out", "both"] = "both",
                       relation: Literal["CALLS", "IMPORTS_FROM", "INHERITS", "REFERENCES", "TESTED_BY"] = "CALLS",
                       limit: int = Query(50, ge=1, le=200), resolved_only: bool = True):
        with database(project) as db:
            return store.neighborhood(db, store.get_node(db, node_id), direction,
                                      relation, limit, resolved_only)

