"""FastAPI application factory. Graph databases are never modified."""
import json
import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.trustedhost import TrustedHostMiddleware

from . import store
from .routes import register_node_routes, register_project_routes
from .explorer_routes import register_connection, register_explorer, register_sources
from .index import IndexCache
from .mcp_client import MCPPool
from .remote import RemoteGraphs
from .sources import SourceRegistry


def configured_projects():
    default = Path.cwd() / "projects.json"
    config = Path(os.environ.get("GRAPHVIEWER_PROJECTS_FILE", default)).resolve()
    values = json.loads(config.read_text(encoding="utf-8")) if config.exists() else {}
    return {name: (config.parent / path).resolve() for name, path in values.items()}


def create_app(projects: dict[str, Path] | None = None, sources_file: Path | None = None):
    pool = MCPPool()

    @asynccontextmanager
    async def lifespan(app):
        yield
        await pool.close()

    app = FastAPI(title="Code Review Graph Viewer", version="0.1.0", lifespan=lifespan)
    registry = configured_projects() if projects is None else projects

    def database(project):
        if project not in registry:
            raise HTTPException(404, "Project not found")
        return store.connect(registry[project])

    @app.get("/health")
    def health():
        return {"status": "ok"}

    register_project_routes(app, database, registry)
    register_node_routes(app, database)
    configure_explorer(app, registry, pool, sources_file)
    return app


def configure_explorer(app, projects, pool, sources_file):
    base = Path(__file__).resolve().parent
    registry = SourceRegistry(sources_file or Path(os.environ.get("GRAPHVIEWER_DATA_DIR", Path.cwd() / ".local")) / "sources.json", projects)
    app.state.source_registry = registry
    remote = RemoteGraphs(pool)
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=["127.0.0.1", "localhost", "testserver"])

    @app.middleware("http")
    async def protect_local_commands(request, call_next):
        origin = request.headers.get("origin")
        if request.method not in ("GET", "HEAD", "OPTIONS") and origin:
            if origin.rstrip("/") != str(request.base_url).rstrip("/"):
                return JSONResponse({"detail": "Cross-origin changes are not allowed"}, status_code=403)
        return await call_next(request)

    register_sources(app, registry, pool, remote)
    register_connection(app, registry, pool, remote)
    register_explorer(app, registry, IndexCache(), pool, remote)
    app.mount("/static", StaticFiles(directory=base / "static"), name="static")

    @app.get("/", include_in_schema=False)
    def frontend():
        return FileResponse(base / "static/index.html")
