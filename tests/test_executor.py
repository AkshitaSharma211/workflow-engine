from engine.executor import run_workflow, run_with_retry


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


def test_retry_succeeds_after_failures():
    calls = {"count": 0}

    def flaky(inputs, config):
        calls["count"] += 1
        if calls["count"] < 3:
            raise ValueError("simulated failure")
        return "success"

    result = run_with_retry(flaky, {}, {}, max_attempts=3, base_delay=0)
    assert result == "success"
    assert calls["count"] == 3