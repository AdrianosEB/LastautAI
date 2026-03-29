from __future__ import annotations

from collections import deque

from pipeline.graph.dag import DAG


class CycleError(Exception):
    pass


def topological_sort(dag: DAG) -> list[str]:
    """Topological sort using Kahn's algorithm. Raises CycleError if cycle detected."""
    in_degree = {node: 0 for node in dag.nodes}
    for edge in dag.edges:
        in_degree[edge.target] += 1

    queue = deque(node for node, degree in in_degree.items() if degree == 0)
    result = []

    while queue:
        node = queue.popleft()
        result.append(node)
        for successor in dag.get_successors(node):
            in_degree[successor] -= 1
            if in_degree[successor] == 0:
                queue.append(successor)

    if len(result) != len(dag.nodes):
        raise CycleError("Graph contains a cycle — topological sort is not possible")

    return result
