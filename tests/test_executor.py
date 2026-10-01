from engine.executor import run_workflow, run_with_retry


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