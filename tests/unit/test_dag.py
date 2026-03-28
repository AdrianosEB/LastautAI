import pytest

from src.graph.dag import DAG
from src.graph.topological import topological_sort, CycleError


class TestDAGNodeOperations:
    def test_add_and_get_node(self):
        dag = DAG()
        dag.add_node("a", {"label": "Step A"})
        assert dag.get_node("a") == {"label": "Step A"}

    def test_get_missing_node(self):
        dag = DAG()
        assert dag.get_node("x") is None

    def test_list_nodes(self):
        dag = DAG()
        dag.add_node("a")
        dag.add_node("b")
        assert set(dag.nodes) == {"a", "b"}

    def test_remove_node(self):
        dag = DAG()
        dag.add_node("a")
        dag.add_node("b")
        dag.add_edge("a", "b")
        dag.remove_node("a")
        assert "a" not in dag.nodes
        assert dag.get_dependencies("b") == []


class TestDAGEdgeOperations:
    def test_add_edge(self):
        dag = DAG()
        dag.add_node("a")
        dag.add_node("b")
        dag.add_edge("a", "b")
        assert dag.get_successors("a") == ["b"]
        assert dag.get_dependencies("b") == ["a"]

    def test_add_conditional_edge(self):
        dag = DAG()
        dag.add_node("a")
        dag.add_node("b")
        dag.add_edge("a", "b", condition="x > 10")
        edge = dag.get_edge("a", "b")
        assert edge is not None
        assert edge.condition == "x > 10"

    def test_edge_with_missing_source_raises(self):
        dag = DAG()
        dag.add_node("b")
        with pytest.raises(ValueError, match="Source node"):
            dag.add_edge("a", "b")

    def test_edge_with_missing_target_raises(self):
        dag = DAG()
        dag.add_node("a")
        with pytest.raises(ValueError, match="Target node"):
            dag.add_edge("a", "b")


class TestCycleDetection:
    def test_no_cycle_in_linear_chain(self):
        dag = DAG()
        for n in ["a", "b", "c"]:
            dag.add_node(n)
        dag.add_edge("a", "b")
        dag.add_edge("b", "c")
        assert dag.has_cycle() is False

    def test_cycle_detected(self):
        dag = DAG()
        for n in ["a", "b", "c"]:
            dag.add_node(n)
        dag.add_edge("a", "b")
        dag.add_edge("b", "c")
        dag.add_edge("c", "a")
        assert dag.has_cycle() is True

    def test_self_loop_is_cycle(self):
        dag = DAG()
        dag.add_node("a")
        dag.add_edge("a", "a")
        assert dag.has_cycle() is True

    def test_empty_graph_no_cycle(self):
        dag = DAG()
        assert dag.has_cycle() is False


class TestTopologicalSort:
    def test_linear_chain(self):
        dag = DAG()
        for n in ["a", "b", "c"]:
            dag.add_node(n)
        dag.add_edge("a", "b")
        dag.add_edge("b", "c")
        result = topological_sort(dag)
        assert result == ["a", "b", "c"]

    def test_fan_out(self):
        dag = DAG()
        for n in ["a", "b", "c"]:
            dag.add_node(n)
        dag.add_edge("a", "b")
        dag.add_edge("a", "c")
        result = topological_sort(dag)
        assert result[0] == "a"
        assert set(result) == {"a", "b", "c"}

    def test_fan_in(self):
        dag = DAG()
        for n in ["a", "b", "c"]:
            dag.add_node(n)
        dag.add_edge("a", "c")
        dag.add_edge("b", "c")
        result = topological_sort(dag)
        assert result[-1] == "c"
        assert set(result) == {"a", "b", "c"}

    def test_cycle_raises(self):
        dag = DAG()
        for n in ["a", "b"]:
            dag.add_node(n)
        dag.add_edge("a", "b")
        dag.add_edge("b", "a")
        with pytest.raises(CycleError):
            topological_sort(dag)

    def test_single_node(self):
        dag = DAG()
        dag.add_node("a")
        assert topological_sort(dag) == ["a"]

    def test_empty_graph(self):
        dag = DAG()
        assert topological_sort(dag) == []

    def test_diamond_shape(self):
        dag = DAG()
        for n in ["a", "b", "c", "d"]:
            dag.add_node(n)
        dag.add_edge("a", "b")
        dag.add_edge("a", "c")
        dag.add_edge("b", "d")
        dag.add_edge("c", "d")
        result = topological_sort(dag)
        assert result[0] == "a"
        assert result[-1] == "d"
        assert result.index("a") < result.index("b")
        assert result.index("a") < result.index("c")
