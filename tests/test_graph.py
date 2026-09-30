import pytest
from engine.graph import topological_sort


def test_straight_line_chain():
    workflow = {"fetch": [], "filter": ["fetch"], "notify": ["filter"]}
    assert topological_sort(workflow) == ["fetch", "filter", "notify"]


def test_cycle_raises_error():
    workflow = {"a": ["b"], "b": ["a"]}
    with pytest.raises(ValueError):
        topological_sort(workflow)