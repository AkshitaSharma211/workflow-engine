from engine.steps import filter_jobs

CONFIG = {
    "keywords": ["machine learning", "ml", "ai", "data", "software", "backend"],
    "level_include": ["intern", "junior", "entry", "graduate"],
    "level_exclude": ["senior", "staff", "principal", "lead", "manager"],
    "locations": ["remote", "india", "worldwide", "anywhere"],
}


def make_job(id, title, location):
    return {"id": id, "title": title, "url": f"https://example.com/{id}", "location": location}


def test_filter_keeps_only_jobs_passing_all_rules():
    jobs = [
        make_job(1, "Machine Learning Intern", "Remote"),           # passes all four rules
        make_job(2, "Senior Machine Learning Engineer", "Remote"),  # fails: excluded level
        make_job(3, "Machine Learning Intern", "San Francisco"),    # fails: wrong location
        make_job(4, "Marketing Intern", "Remote"),                  # fails: no keyword
        make_job(5, "Machine Learning Engineer", "Remote"),         # fails: no level word
    ]
    result = filter_jobs({"fetch": jobs}, CONFIG)
    assert [j["id"] for j in result] == [1]