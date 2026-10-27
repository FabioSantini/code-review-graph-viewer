"""Explorer API: source management, bounded projections and MCP capability checks."""
import asyncio
from pathlib import Path
from typing import Literal

from fastapi import HTTPException, Query, Response
from starlette.concurrency import run_in_threadpool

from . import explore
from .sources import SourceInput

View = Literal["files", "classes", "functions", "methods", "folders", "languages", "architecture"]


def register_sources(app, registry, pool, remote):
    @app.get("/api/sources")
    def sources():
        return registry.all()

    @app.post("/api/sources", status_code=201)
    def add_source(value: SourceInput):
        return registry.save(value)

    @app.put("/api/sources/{identity}")
    async def edit_source(identity: str, value: SourceInput):
        item = registry.save(value, identity)
        await pool.close(identity)
        remote.cache.pop(identity, None)
        return item

    @app.delete("/api/sources/{identity}", status_code=204)
    async def delete_source(identity: str):
        registry.remove(identity)
        await pool.close(identity)
        remote.cache.pop(identity, None)
        return Response(status_code=204)


async def checked_call(pool, source, name, args):
    try:
        return await pool.call(source, name, args)
    except (Exception, asyncio.TimeoutError) as exc:
        raise HTTPException(502, "MCP connection failed: " + str(exc)[:350]) from exc


def register_connection(app, registry, pool, remote):
    @app.post("/api/sources/{identity}/refresh")
    async def refresh_source(identity: str):
        registry.get(identity)
        remote.cache.pop(identity, None)
        return {"refreshed": True}

    @app.post("/api/sources/{identity}/connect")
    async def connect_source(identity: str):
        source = registry.get(identity)
        await pool.close(identity)
        remote.cache.pop(identity, None)
        if source["transport"] == "local":
            if not Path(source["database_path"]).is_file():
                raise HTTPException(503, "Local graph index not found")
            return {"connected": True, "tools": [], "mode": "local"}
        result = await checked_call(pool, source, "list_graph_stats_tool", {})
        tools = await pool.worker(source).ready
        return {"connected": True, "tools": tools, "statistics": result, "mode": "mcp"}


def register_explorer(app, registry, cache, pool, remote):
    async def index_for(identity):
        source = registry.get(identity)
        if source.get("database_path"):
            return source, await run_in_threadpool(cache.get, source), False
        try:
            return source, await remote.catalog_index(source), True
        except Exception as exc:
            raise HTTPException(502, "Unable to browse this MCP graph: " + str(exc)[:250]) from exc

    @app.get('/api/sources/{identity}/revision')
    def source_revision(identity: str):
        import hashlib
        source=registry.get(identity)
        if not source.get('database_path'):
            return {'supported':False,'revision':None}
        db=Path(source['database_path']).resolve()
        signatures=[]
        for path in (db,Path(str(db)+'-wal')):
            try:
                stat=path.stat();signatures.append((stat.st_mtime_ns,stat.st_size))
            except OSError:signatures.append(None)
        revision=hashlib.sha256(repr(signatures).encode()).hexdigest()[:24]
        return {'supported':True,'available':signatures[0] is not None,'revision':revision}

    @app.get("/api/explore/{identity}/catalog")
    async def catalog(identity: str, view: View = "files", q: str = "", language: str = "",
                      folder: str = "", tests: bool = False, limit: int = Query(50, ge=1, le=100),
                      offset: int = Query(0, ge=0)):
        _, index, partial = await index_for(identity)
        result = await run_in_threadpool(explore.catalog, index, view, q, language, folder, tests, limit, offset)
        result["partial"] = partial
        result["languages"] = sorted({node.get("language", "") for node in index.nodes.values()} - {""})
        result["indexed_nodes"] = len(index.nodes)
        return result

    network_cache = {}

    @app.get('/api/explore/{identity}/file-network')
    async def file_network(identity: str, key: str = '', tests: bool = False, resolved_only: bool = True,
                           relation: str = '', language: str = '', folder: str = '', depth: int = Query(2, ge=1, le=10)):
        from .file_network import FileNetwork
        _, index, partial = await index_for(identity)
        if partial:
            raise HTTPException(409, 'Complete file navigation requires a local graph index')
        signature = (identity, tests, resolved_only, relation, language, folder)
        cached = network_cache.get(signature)
        if not cached or cached[0] is not index:
            network = await run_in_threadpool(FileNetwork, index, tests, resolved_only, relation, language, folder)
            if len(network_cache) > 32: network_cache.clear()
            network_cache[signature] = (index, network)
        network = network_cache[signature][1]
        components = network.components()
        master = key or (components[0]['master'] if components else '')
        result = await run_in_threadpool(network.graph, master, depth) if master else {'nodes': [], 'edges': [], 'layered': True, 'core': None}
        result['components'] = components
        result['languages'] = sorted({n.get('language', '') for n in index.nodes.values()} - {''})
        return result

    @app.get('/api/explore/{identity}/network')
    async def projected_network(identity: str, view: View = 'files', key: str = '', tests: bool = False,
                                resolved_only: bool = True, relation: str = '', language: str = '', folder: str = '',
                                depth: int = Query(2, ge=1, le=10), class_key: str = ''):
        from .projected_network import ProjectedNetwork
        from .file_network import FileNetwork
        _, index, partial = await index_for(identity)
        if partial:
            raise HTTPException(409, 'Complete navigation requires a local graph index')
        signature=(identity,view,tests,resolved_only,relation,language,folder)
        cached=network_cache.get(signature)
        if not cached or cached[0] is not index:
            constructor=FileNetwork if view=='files' else ProjectedNetwork
            args=(index,) if view=='files' else (index,view)
            network=await run_in_threadpool(constructor,*args,tests,resolved_only,relation,language,folder)
            if len(network_cache)>32:network_cache.clear()
            network_cache[signature]=(index,network)
        network=network_cache[signature][1]
        components=network.components()
        master=key or (components[0]['master'] if components else '')
        if class_key and view=='methods' and not key:master=''
        result=await run_in_threadpool(network.graph,master,depth) if master else dict(core=None,nodes=[],edges=[],layered=True)
        result['components']=components
        result['view']=view
        result['languages']=sorted({n.get('language','') for n in index.nodes.values()}-{''})
        if view in ('folders','languages','architecture'):
            result['navigation']=list(network.nodes.values())
        if view=='methods' and class_key:
            result['class_methods']=[n for n in network.nodes.values() if n.get('class_key')==class_key]
        return result

    register_drilldown(app, index_for, pool, remote)

    @app.get('/api/explore/{identity}/code')
    async def code(identity: str, key: str):
        from .code_view import read_code
        source, index, _ = await index_for(identity)
        node = index.nodes.get(key)
        if not node:
            raise HTTPException(404, 'Indexed element not found')
        return await run_in_threadpool(read_code, source, node)


def register_drilldown(app, index_for, pool, remote):
    @app.get("/api/explore/{identity}/children")
    async def children(identity: str, key: str, limit: int = Query(50, ge=1, le=100), offset: int = Query(0, ge=0)):
        source, index, partial = await index_for(identity)
        if partial and not key.startswith("@"):
            return await remote.children(source, key, limit, offset)
        return await run_in_threadpool(explore.children, index, key, limit, offset)

    @app.get("/api/explore/{identity}/graph")
    async def graph(identity: str, key: str, view: View = "files", resolved_only: bool = True,
                    relation: Literal["", "CALLS", "IMPORTS_FROM", "INHERITS", "REFERENCES", "TESTED_BY"] = "",
                    limit: int = Query(24, ge=1, le=60), language: str = "", folder: str = "", tests: bool = False):
        source, index, partial = await index_for(identity)
        core = explore.projected_node(index, key, view)
        if partial and (view not in ("functions", "methods") or relation not in ("", "CALLS")):
            return {"core": core, "nodes": [], "edges": [], "incoming": [], "outgoing": [],
                    "partial": True, "notice": "This remote MCP view supports function/method calls. Attach a local CRG index for aggregated dependencies and other relations."}
        if partial:
            return await remote.graph(source, core, resolved_only, limit, language, folder, tests)
        return await run_in_threadpool(explore.neighborhood, index, view, key, limit,
                                       resolved_only, relation, language, folder, tests)
