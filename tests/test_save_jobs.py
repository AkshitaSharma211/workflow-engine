from engine.db import SessionLocal, Job


def login_new_user(client, email="a@example.com"):
    r = client.post("/signup", json={"email": email, "password": "password123"})
    assert r.status_code == 201


def titles(response):
    return [j["title"] for j in response.json()["jobs"]]


def test_lists_all_open_jobs(client, seeded_jobs):
    login_new_user(client)
    assert client.get("/jobs").json()["total"] == 3


def test_search_matches_whole_words_only(client, seeded_jobs):
    login_new_user(client)
    # "Internal" contains "intern" as letters, but is a different word
    assert titles(client.get("/jobs", params={"q": "intern"})) == ["Machine Learning Intern"]


def test_search_needs_every_word_to_match(client, seeded_jobs):
    login_new_user(client)
    assert client.get("/jobs", params={"q": "machine intern"}).json()["total"] == 1
    assert client.get("/jobs", params={"q": "machine analyst"}).json()["total"] == 0


def test_company_filter(client, seeded_jobs):
    login_new_user(client)
    assert titles(client.get("/jobs", params={"company": "globex"})) == ["Data Analyst"]


def test_remote_filter(client, seeded_jobs):
    login_new_user(client)
    assert client.get("/jobs", params={"remote": "true"}).json()["total"] == 2


def test_closed_jobs_are_hidden_unless_asked_for(client, seeded_jobs):
    login_new_user(client)
    with SessionLocal() as s:
        s.query(Job).filter(Job.job_id == 3).update({"is_open": False})
        s.commit()
    assert client.get("/jobs").json()["total"] == 2
    assert client.get("/jobs", params={"open_only": "false"}).json()["total"] == 3


def test_marking_a_job_shows_on_the_job_and_in_the_status_tab(client, seeded_jobs):
    login_new_user(client)
    pk = seeded_jobs[1]
    assert client.put(f"/jobs/{pk}/status", json={"status": "applied"}).status_code == 200

    marks = {j["id"]: j["my_status"] for j in client.get("/jobs").json()["jobs"]}
    assert marks[pk] == "applied"

    tab = client.get("/jobs", params={"status": "applied", "open_only": "false"}).json()
    assert [j["id"] for j in tab["jobs"]] == [pk]


def test_clearing_a_status_removes_the_mark(client, seeded_jobs):
    login_new_user(client)
    pk = seeded_jobs[1]
    client.put(f"/jobs/{pk}/status", json={"status": "saved"})
    client.put(f"/jobs/{pk}/status", json={"status": "none"})
    tab = client.get("/jobs", params={"status": "saved", "open_only": "false"}).json()
    assert tab["total"] == 0


def test_status_is_private_to_each_user(client, other_client, seeded_jobs):
    login_new_user(client, "a@example.com")
    login_new_user(other_client, "b@example.com")
    pk = seeded_jobs[1]
    client.put(f"/jobs/{pk}/status", json={"status": "applied"})

    marks = {j["id"]: j["my_status"] for j in other_client.get("/jobs").json()["jobs"]}
    assert marks[pk] is None
    tab = other_client.get("/jobs", params={"status": "applied", "open_only": "false"}).json()
    assert tab["total"] == 0


def test_invalid_status_is_rejected(client, seeded_jobs):
    login_new_user(client)
    r = client.put(f"/jobs/{seeded_jobs[1]}/status", json={"status": "bogus"})
    assert r.status_code == 422


def test_marking_a_missing_job_gives_404(client):
    login_new_user(client)
    assert client.put("/jobs/999999/status", json={"status": "saved"}).status_code == 404


def test_stats_reflect_jobs_and_my_marks(client, seeded_jobs):
    login_new_user(client)
    client.put(f"/jobs/{seeded_jobs[1]}/status", json={"status": "applied"})
    d = client.get("/stats").json()
    assert d["open_jobs"] == 3
    assert d["mine"] == {"saved": 0, "applied": 1, "ignored": 0}
    assert d["last_updated"] is not None
    assert len(d["newest"]) == 3