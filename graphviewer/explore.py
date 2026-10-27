"""Projection and filtering of graph entities into navigable views."""
from collections import Counter

from fastapi import HTTPException

VIEWS = ("files", "classes", "functions", "methods", "folders", "languages", "architecture")


def group_key(node, view):
    if view == "languages":
        return node.get("language") or "unknown"
    folder = node.get("folder", ".")
    return "/".join(folder.split("/")[:2]) if view == "architecture" else folder


def group_node(key, view, count):
    return {"key": "@" + view + ":" + key, "name": key, "kind": view.title(),
            "category": view, "path": key, "member_count": count}


def visible(node, language, folder, tests):
    return ((not language or node.get("language") == language)
            and (not folder or node.get("path", "").startswith(folder))
            and (tests or not node.get("is_test", node.get("kind") == "Test")))


def catalog(index, view, q="", language="", folder="", tests=False, limit=50, offset=0):
    nodes = [node for node in index.nodes.values() if visible(node, language, folder, tests)]
    if view in ("folders", "languages", "architecture"):
        counts = Counter(group_key(node, view) for node in nodes if node["kind"] == "File")
        items = [group_node(key, view, count) for key, count in counts.items()]
    else:
        items = [node for node in nodes if node["category"] == view]
    items = [node for node in items if q.casefold() in (node["name"] + " " + node.get("path", "")).casefold()]
    items.sort(key=lambda node: (node.get("path", ""), node["name"], node["key"]))
    return {"items": items[offset:offset + limit], "total": len(items),
            "offset": offset, "limit": limit, "partial": False}


def children(index, key, limit=100, offset=0):
    if key.startswith("@"):
        view, value = key[1:].split(":", 1)
        items = [node for node in index.nodes.values()
                 if node["kind"] == "File" and group_key(node, view) == value]
    else:
        if key not in index.nodes:
            raise HTTPException(404, "Node not found")
        items = [index.nodes[child] for child in index.contents.get(key, []) if child in index.nodes]
    items.sort(key=lambda node: (node["category"], node["name"]))
    return {"items": items[offset:offset + limit], "total": len(items), "offset": offset, "limit": limit}


def projected_key(index, key, view):
    if view in ("folders", "languages", "architecture"):
        node = index.nodes.get(key)
        return "@" + view + ":" + group_key(node, view) if node else None
    return index.owner(key, view)


def projected_node(index, key, view):
    if key.startswith("@"):
        value = key.split(":", 1)[1]
        count = sum(node["kind"] == "File" and group_key(node, view) == value for node in index.nodes.values())
        if not count:
            raise HTTPException(404, "Group not found")
        return group_node(value, view, count)
    if key not in index.nodes:
        raise HTTPException(404, "Node not found")
    return index.nodes[key]


def dependency_edges(index, view, key, resolved_only, relation, language, folder, tests):
    counts = Counter()
    for edge in index.edges:
        if edge["kind"] == "CONTAINS" or (relation and edge["kind"] != relation):
            continue
        if resolved_only and edge["kind"] == "CALLS" and edge.get("target_resolution") != "direct":
            continue
        source = index.nodes.get(edge["source_qualified"])
        target = index.nodes.get(edge["target_qualified"])
        if not source or not target or not all(visible(n, language, folder, tests) for n in (source, target)):
            continue
        left = projected_key(index, edge["source_qualified"], view)
        right = projected_key(index, edge["target_qualified"], view)
        if left and right and left != right and key in (left, right):
            counts[left, right, edge["kind"]] += 1
    return counts


def neighborhood(index, view, key, limit=24, resolved_only=True, relation="", language="", folder="", tests=False):
    core = projected_node(index, key, view)
    counts = dependency_edges(index, view, key, resolved_only, relation, language, folder, tests)
    ordered = sorted(counts.items(), key=lambda item: (-item[1], item[0]))
    names = []
    for (source, target, _), _count in ordered:
        neighbor = target if source == key else source
        if neighbor not in names:
            names.append(neighbor)
    included = set(names[:limit]) | {key}
    edges = [{"source": s, "target": t, "kind": k, "count": count}
             for (s, t, k), count in ordered if s in included and t in included]
    incoming = {edge["source"] for edge in edges if edge["target"] == key}
    outgoing = {edge["target"] for edge in edges if edge["source"] == key}
    nodes = [projected_node(index, name, view) for name in names[:limit]]
    return {"core": core, "nodes": nodes, "edges": edges,
            "incoming": [node for node in nodes if node["key"] in incoming],
            "outgoing": [node for node in nodes if node["key"] in outgoing],
            "total_neighbors": len(names), "truncated": len(names) > limit, "partial": False}
