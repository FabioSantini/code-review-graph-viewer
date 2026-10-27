"""CRG MCP adapter for sources whose SQLite index is not on this computer."""
from .index import GraphIndex, normalize
from .explore import visible


class RemoteGraphs:
    def __init__(self, pool):
        self.pool, self.cache = pool, {}

    async def catalog_index(self, source):
        if source["id"] in self.cache:
            return self.cache[source["id"]]
        result = await self.pool.call(source, "list_communities_tool", {"max_results": 100, "max_members": 1})
        nodes = {}
        for community in result.get("communities", [])[:100]:
            detail = await self.pool.call(source, "get_community_tool", {
                "community_id": community["id"], "include_members": True, "max_members": 100})
            for node in detail.get("community", {}).get("member_details", []):
                nodes[node["qualified_name"]] = node
        index = GraphIndex(list(nodes.values()), [], source.get("repo_root", ""))
        self.cache[source["id"]] = index
        return index

    async def search(self, source, query, kind):
        result = await self.pool.call(source, "semantic_search_nodes_tool", {
            "query": query, "kind": kind, "limit": 50})
        return [normalize(node) for node in result.get("results", [])]

    def remember(self, source, nodes, edges=()):
        previous = self.cache[source["id"]]
        combined = dict(previous.nodes)
        for node in nodes:
            key = node.get("qualified_name", node.get("key"))
            if key:
                combined[key] = {**combined.get(key, {}), **node, "qualified_name": key}
        index = GraphIndex(list(combined.values()), previous.edges + list(edges), source.get("repo_root", ""))
        self.cache[source["id"]] = index
        return index

    async def children(self, source, key, limit=50, offset=0):
        result = await self.pool.call(source, "query_graph_tool", {
            "pattern": "children_of", "target": key, "max_results": 100})
        nodes = result.get("results", [])
        edges = [{"kind": "CONTAINS", "source_qualified": key, "target_qualified": node["qualified_name"]}
                 for node in nodes]
        index = self.remember(source, nodes, edges)
        items = [index.nodes[node["qualified_name"]] for node in nodes]
        return {"items": items[offset:offset + limit], "total": len(items),
                "available_total": result.get("result_count", len(items)), "offset": offset,
                "limit": limit, "partial": bool(result.get("results_omitted", 0))}

    async def graph(self, source, core, resolved_only, limit=24, language="", folder="", tests=False):
        nodes, edges, incoming, outgoing = {}, [], [], []
        for pattern, direction in (("callers_of", "in"), ("callees_of", "out")):
            result = await self.pool.call(source, "query_graph_tool", {
                "pattern": pattern, "target": core["key"], "max_results": 24,
                "resolution": "direct" if resolved_only else "all"})
            for node in result.get("results", []):
                item = normalize(node)
                nodes[item["key"]] = item
                (incoming if direction == "in" else outgoing).append(item)
            for edge in result.get("edges", []):
                edges.append({"source": edge["source"], "target": edge["target"],
                              "kind": edge["kind"], "count": 1})
        index = self.remember(source, list(nodes.values()))
        return bounded_graph(index, core, nodes, edges, incoming, outgoing,
                             limit, language, folder, tests)


def bounded_graph(index, core, nodes, edges, incoming, outgoing, limit, language, folder, tests):
    candidates = [index.nodes[key] for key in nodes if key in index.nodes and key != core["key"]]
    candidates = [node for node in candidates if visible(node, language, folder, tests)]
    selected = candidates[:limit]
    allowed = {node["key"] for node in selected}
    inbound = {node["key"] for node in incoming}
    outbound = {node["key"] for node in outgoing}
    return {"core": core, "nodes": selected,
            "edges": [edge for edge in edges if edge["source"] in allowed | {core["key"]}
                      and edge["target"] in allowed | {core["key"]}],
            "incoming": [node for node in selected if node["key"] in inbound],
            "outgoing": [node for node in selected if node["key"] in outbound],
            "total_neighbors": len(candidates), "partial": True, "truncated": len(candidates) > limit}
