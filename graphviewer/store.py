"""Bounded, read-only queries against existing CRG databases."""
import sqlite3
from contextlib import contextmanager
from pathlib import Path

from fastapi import HTTPException


@contextmanager
def connect(path: Path):
    try:
        db = sqlite3.connect(path.resolve().as_uri() + "?mode=ro", uri=True, timeout=3)
    except sqlite3.Error as exc:
        raise HTTPException(503, "Graph database unavailable") from exc
    db.row_factory = sqlite3.Row
    try:
        db.execute("PRAGMA query_only=ON")
        yield db
    except sqlite3.Error as exc:
        raise HTTPException(503, "Graph schema unavailable or incompatible") from exc
    finally:
        db.close()


def overview(db):
    kinds = {row[0]: row[1] for row in db.execute("SELECT kind, COUNT(*) FROM nodes GROUP BY kind")}
    edges = db.execute("SELECT COUNT(*) FROM edges").fetchone()[0]
    languages = [row[0] for row in db.execute("SELECT DISTINCT language FROM nodes ORDER BY language")]
    return {"nodes": sum(kinds.values()), "edges": edges, "kinds": kinds, "languages": languages}


def get_node(db, node_id):
    row = db.execute("SELECT * FROM nodes WHERE id=?", (node_id,)).fetchone()
    if row is None:
        raise HTTPException(404, "Node not found")
    return dict(row)


def children(db, core):
    rows = db.execute(
        "SELECT DISTINCT n.* FROM edges e JOIN nodes n ON n.qualified_name=e.target_qualified "
        "WHERE e.source_qualified=? AND e.kind='CONTAINS' ORDER BY n.kind,n.name LIMIT 500",
        (core["qualified_name"],),
    )
    return [dict(row) for row in rows]


def neighborhood(db, core, direction, relation, limit, resolved_only):
    identity = core["qualified_name"]
    conditions = {"in": "target_qualified=?", "out": "source_qualified=?",
                  "both": "(source_qualified=? OR target_qualified=?)"}
    args = [identity, identity] if direction == "both" else [identity]
    where = conditions[direction] + " AND kind=?"
    args.append(relation)
    if resolved_only:
        where += " AND (kind<>'CALLS' OR target_resolution='direct')"
    rows = db.execute(f"SELECT * FROM edges WHERE {where} ORDER BY id LIMIT ?", (*args, limit + 1))
    found = [dict(row) for row in rows]
    edges = found[:limit]
    names = {edge[key] for edge in edges for key in ("source_qualified", "target_qualified")} - {identity}
    nodes = []
    if names:
        slots = ",".join("?" for _ in names)
        nodes = [dict(row) for row in db.execute(
            f"SELECT * FROM nodes WHERE qualified_name IN ({slots}) ORDER BY name", tuple(names))]
    return {"core": core, "nodes": nodes, "edges": edges, "truncated": len(found) > limit}
