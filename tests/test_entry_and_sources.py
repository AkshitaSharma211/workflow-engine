import time
import datetime

from engine.db import SessionLocal, Job
from engine.sources import stable_id
from engine.steps import filter_jobs, save_jobs

CONFIG = {
    "keywords": ["data", "engineer", "software"],
    "level_include": ["intern", "junior"],
    "level_exclude": ["senior", "staff"],
    "locations": ["remote", "india"],
    "location_exclude": ["usa only", "united states"],
}


def job(i, title, location="Remote", level="", source="greenhouse", company="acme"):
    return {"id": i, "title": title, "url": f"https://e.com/{i}", "location": location,
            "company": company, "source": source, "level": level}


def add_rows(rows):
    now = datetime.datetime.utcnow()
    with SessionLocal() as s:
        for j in rows:
            s.add(Job(job_id=j["id"], title=j["title"], company=j["company"], url=j["url"],
                      location=j["location"], source=j["source"], level=j["level"],
                      first_seen=now, last_seen=now, is_open=True))
        s.commit()


def signup(client):
    r = client.post("/signup", json={"email": "a@example.com", "password": "password123"})
    assert r.status_code == 201


# ---- filter step ----

def test_filter_accepts_level_field_even_without_a_level_word_in_the_title():
    j = job(1, "Data Engineer", level="Internship")
    assert [x["id"] for x in filter_jobs({"fetch_muse": [j]}, CONFIG)] == [1]


def test_filter_merges_jobs_from_every_source():
    a = job(1, "Software Intern")
    b = job(2, "Data Intern", source="lever")
    result = filter_jobs({"fetch": [a], "fetch_lever": [b]}, CONFIG)
    assert sorted(x["id"] for x in result) == [1, 2]


def test_filter_drops_us_only_remote_jobs():
    j = job(1, "Software Intern", location="Remote - USA Only")
    assert filter_jobs({"fetch": [j]}, CONFIG) == []


# ---- search API ----

def test_entry_toggle_keeps_entry_level_and_drops_senior(client):
    signup(client)
    add_rows([
        job(1, "Software Intern"),
        job(2, "Senior Software Engineer"),
        job(3, "Backend Developer", level="Entry Level", source="muse"),
        job(4, "Internal Tools Engineer"),
    ])
    r = client.get("/jobs", params={"entry": "true"}).json()
    assert sorted(j["title"] for j in r["jobs"]) == ["Backend Developer", "Software Intern"]


def test_source_filter(client):
    signup(client)
    add_rows([job(1, "A", source="muse"), job(2, "B", source="lever"), job(3, "C", source="lever")])
    assert client.get("/jobs", params={"source": "lever"}).json()["total"] == 2


# ---- saving ----

def test_aggregator_jobs_are_never_closed():
    save_jobs({"fetch": [job(1, "A", source="greenhouse", company="acme"),
                         job(2, "B", source="muse", company="Muse Co")]}, {})
    time.sleep(0.01)
    result = save_jobs({"fetch": [job(1, "A", source="greenhouse", company="acme")]}, {})
    assert result["closed"] == 0
    with SessionLocal() as s:
        assert s.query(Job).filter(Job.is_open.is_(True)).count() == 2


def test_stable_id_is_deterministic_and_fits_bigint():
    assert stable_id("lever", "x") == stable_id("lever", "x")
    assert stable_id("lever", "x") != stable_id("ashby", "x")
    assert 0 <= stable_id("lever", "x") < 2**63