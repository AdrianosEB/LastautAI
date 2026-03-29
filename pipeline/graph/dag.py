from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class Edge:
    source: str
    target: str
    condition: str | None = None


class DAG:
    """Directed Acyclic Graph for workflow step ordering."""

    def __init__(self):
        self._nodes: dict[str, dict[str, Any]] = {}
        self._edges: list[Edge] = []
        self._adjacency: dict[str, list[str]] = {}
        self._reverse: dict[str, list[str]] = {}

    def add_node(self, node_id: str, metadata: dict[str, Any] | None = None) -> None:
        self._nodes[node_id] = metadata or {}
        self._adjacency.setdefault(node_id, [])
        self._reverse.setdefault(node_id, [])

    def add_edge(self, source: str, target: str, condition: str | None = None) -> None:
        if source not in self._nodes:
            raise ValueError(f"Source node '{source}' not in graph")
        if target not in self._nodes:
            raise ValueError(f"Target node '{target}' not in graph")
        edge = Edge(source=source, target=target, condition=condition)
        self._edges.append(edge)
        self._adjacency[source].append(target)
        self._reverse[target].append(source)

    def get_node(self, node_id: str) -> dict[str, Any] | None:
        return self._nodes.get(node_id)

    def get_dependencies(self, node_id: str) -> list[str]:
        return list(self._reverse.get(node_id, []))

    def get_successors(self, node_id: str) -> list[str]:
        return list(self._adjacency.get(node_id, []))

    def get_edge(self, source: str, target: str) -> Edge | None:
        for edge in self._edges:
            if edge.source == source and edge.target == target:
                return edge
        return None

    @property
    def nodes(self) -> list[str]:
        return list(self._nodes.keys())

    @property
    def edges(self) -> list[Edge]:
        return list(self._edges)

    def has_cycle(self) -> bool:
        WHITE, GRAY, BLACK = 0, 1, 2
        color = {n: WHITE for n in self._nodes}

        def dfs(node: str) -> bool:
            color[node] = GRAY
            for neighbor in self._adjacency.get(node, []):
                if color[neighbor] == GRAY:
                    return True
                if color[neighbor] == WHITE and dfs(neighbor):
                    return True
            color[node] = BLACK
            return False

        for node in self._nodes:
            if color[node] == WHITE:
                if dfs(node):
                    return True
        return False

    def remove_node(self, node_id: str) -> None:
        if node_id not in self._nodes:
            return
        del self._nodes[node_id]
        self._edges = [e for e in self._edges if e.source != node_id and e.target != node_id]
        del self._adjacency[node_id]
        del self._reverse[node_id]
        for adj_list in self._adjacency.values():
            while node_id in adj_list:
                adj_list.remove(node_id)
        for rev_list in self._reverse.values():
            while node_id in rev_list:
                rev_list.remove(node_id)
