from engine.executor import run_workflow


def test_simple_chain_runs_in_order():
    def add_one(inputs, config):
        prev = list(inputs.values())[0] if inputs else 0
        return prev + 1

    steps = {
        "a": {"deps": [], "type": "add_one"},
        "b": {"deps": ["a"], "type": "add_one"},
    }
    registry = {"add_one": add_one}

    result = run_workflow(steps, registry)
    assert result == {"a": 1, "b": 2}