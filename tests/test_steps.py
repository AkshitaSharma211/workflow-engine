from engine.steps import fetch_jobs


def test_fetch_jobs_returns_real_data():
    result = fetch_jobs({}, {"board": "stripe"})
    assert isinstance(result, list)
    assert len(result) > 0
    assert "title" in result[0]
    assert "url" in result[0]
    print(result[0])  # just to see one real job