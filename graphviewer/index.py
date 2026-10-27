"""Normalized local graph, read from SQLite and invalidated by DB/WAL changes."""
from pathlib import Path

from .store import connect


def normalize(node, category=None):
    key = node.get("qualified_name", str(node.get("id", "")))
    name = node.get("name", key)
    if node.get("kind") == "File":
        name = name.replace("\\", "/").rsplit("/", 1)[-1]
    return {**node, "key": key, "name": name,
            "category": category or {"File": "files", "Class": "classes", "Test": "tests"}.get(node.get("kind"), "functions")}


class GraphIndex:
    def __init__(self, nodes, edges, root=""):
        self.nodes = {node["qualified_name"]: normalize(node) for node in nodes}
        self.edges, self.root = edges, root.replace("\\", "/").rstrip("/")
        self.parents, self.contents = {}, {}
        self._containment()
        self._classify()

    def _containment(self):
        for edge in self.edges:
            if edge["kind"] != "CONTAINS":
                continue
            source, target = edge["source_qualified"], edge["target_qualified"]
            self.parents[target] = source
            self.contents.setdefault(source, []).append(target)

    def _classify(self):
        classes = {(node.get("file_path"), node["name"]): node["key"]
                   for node in self.nodes.values() if node["kind"] == "Class"}
        for key, node in self.nodes.items():
            candidate = classes.get((node.get("file_path"), node.get("parent_name")))
            if key not in self.parents and candidate:
                self.parents[key] = candidate
                self.contents.setdefault(candidate, []).append(key)
            parent = self.nodes.get(self.parents.get(key), {})
            if parent.get("kind") == "Class" and node["kind"] in ("Function", "Test"):
                node["category"] = "methods"
            path = node.get("file_path", "").replace("\\", "/")
            node["path"] = path.removeprefix(self.root + "/") if self.root else path
            node["folder"] = node["path"].rsplit("/", 1)[0] if "/" in node["path"] else "."

    def owner(self, key, view):
        node = self.nodes.get(key)
        if not node:
            return None
        if view in ("functions", "methods"):
            return key if node["category"] in ("functions", "methods") else None
        if view == "files":
            return node.get("file_path")
        if view == "classes":
            for _ in range(20):
                if node.get("kind") == "Class":
                    return node["key"]
                node = self.nodes.get(self.parents.get(node["key"]))
                if not node:
                    break
        return None


class IndexCache:
    def __init__(self):
        self.entries = {}

    def get(self, source):
        path = Path(source["database_path"]).resolve()
        signature = tuple((p.stat().st_mtime_ns, p.stat().st_size) if p.exists() else None
                          for p in (path, Path(str(path) + "-wal")))
        cached = self.entries.get(str(path))
        if cached and cached[0] == signature:
            return cached[1]
        with connect(path) as db:
            nodes = [dict(row) for row in db.execute("SELECT * FROM nodes")]
            edges = [dict(row) for row in db.execute("SELECT * FROM edges")]
        index = GraphIndex(nodes, edges, source.get("repo_root", ""))
        self.entries[str(path)] = (signature, index)
        return index
