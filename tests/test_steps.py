from engine.steps import fetch_jobs, filter_jobs


def test_fetch_jobs_returns_real_data():
    result = fetch_jobs({}, {"board": "stripe"})
    assert isinstance(result, list)
    assert len(result) > 0
    assert "title" in result[0]
    assert "url" in result[0]
    print(result[0])  # just to see one real job


def test_filter_jobs_keeps_only_matching_titles():
    jobs = [
        {"id": 1, "title": "Backend Intern", "url": "x", "location": "Pune"},
        {"id": 2, "title": "Senior Engineer", "url": "y", "location": "Mumbai"},
        {"id": 3, "title": "Data Science Intern", "url": "z", "location": "Delhi"},
    ]
    result = filter_jobs({"fetch": jobs}, {"keyword": "intern"})
    assert len(result) == 2
    assert all("intern" in job["title"].lower() for job in result)