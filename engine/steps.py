import requests
import datetime
from sqlalchemy.dialects.postgresql import insert as pg_insert
from engine.db import SessionLocal, SeenJob, Job
import os
from dotenv import load_dotenv
import re

load_dotenv()

COMPLETE_SOURCES = {"greenhouse", "lever", "ashby"}


def _all_jobs(inputs: dict) -> list:
    """Merge the job lists from every fetch step feeding this step."""
    jobs = []
    for value in inputs.values():
        if isinstance(value, list):
            jobs.extend(value)
    return jobs

def fetch_jobs(inputs: dict, config: dict) -> list:
    """
    config: {"boards": ["stripe", "airbnb", ...]}
    Returns simplified job dicts from every board that responds.
    """
    boards = config["boards"]
    simplified = []
    failed = 0

    for board in boards:
        url = f"https://boards-api.greenhouse.io/v1/boards/{board}/jobs"
        try:
            response = requests.get(url, timeout=30)
            response.raise_for_status()
        except requests.RequestException as e:
            failed += 1
            print(f"fetch_jobs: skipping '{board}': {e}")
            continue

        for job in response.json()["jobs"]:
            location = (job.get("location") or {}).get("name", "Unknown")
            simplified.append({
                "id": job["id"],
                "title": job["title"],
                "url": job["absolute_url"],
                "location": location,
                "company": board,
                "source": "greenhouse",
            })

    if failed == len(boards):
        raise RuntimeError("fetch_jobs: every board failed")

    print(f"fetch_jobs: {len(simplified)} jobs from {len(boards) - failed}/{len(boards)} boards")
    return simplified

def _has_word(text: str, words: list) -> bool:
    """True if any of `words` appears in `text` as a whole word or phrase."""
    return any(re.search(rf"\b{re.escape(w)}\b", text) for w in words)

def filter_jobs(inputs: dict, config: dict) -> list:
    jobs = _all_jobs(inputs)
    keywords = [w.lower() for w in config["keywords"]]
    level_include = [w.lower() for w in config["level_include"]]
    level_exclude = [w.lower() for w in config["level_exclude"]]
    locations = [w.lower() for w in config["locations"]]
    location_exclude = [w.lower() for w in config.get("location_exclude", [])]

    filtered = []
    for job in jobs:
        title = job["title"].lower()
        location = job["location"].lower()
        level = (job.get("level") or "").lower()

        if not _has_word(title, keywords):
            continue
        if level_include and level not in ("internship", "entry level") \
                and not _has_word(title, level_include):
            continue
        if _has_word(title, level_exclude):
            continue
        if not _has_word(location, locations):
            continue
        if any(w in location for w in location_exclude):
            continue
        filtered.append(job)
    return filtered

def dedupe(inputs: dict, config: dict) -> list:
    """
    inputs: {"filter": [list of jobs from filter_jobs]}
    Returns only jobs whose id is NOT already in seen_jobs.
    """
    jobs = inputs["filter"]
    session = SessionLocal()

    try:
        new_jobs = []
        for job in jobs:
            if session.query(SeenJob).filter_by(job_id=job["id"]).first() is None:
                new_jobs.append(job)
        return new_jobs
    finally:
        session.close()


def telegram_alert(inputs: dict, config: dict) -> list:
    jobs = inputs["dedupe"]
    if not jobs:
        return []

    max_jobs = config.get("max_jobs", 10)
    shown = jobs[:max_jobs]
    remaining = len(jobs) - len(shown)

    lines = [f"{j['title']} ({j['location']}) - {j['url']}" for j in shown]
    message = "New jobs found:\n" + "\n".join(lines)
    if remaining > 0:
        message += f"\n...and {remaining} more"

    token = os.environ["TELEGRAM_BOT_TOKEN"]
    chat_id = os.environ["TELEGRAM_CHAT_ID"]
    url = f"https://api.telegram.org/bot{token}/sendMessage"

    response = requests.post(url, data={"chat_id": chat_id, "text": message}, timeout=10)
    response.raise_for_status()
    return shown


def mark_seen(inputs: dict, config: dict) -> str:
    """inputs: {"notify": jobs that were actually sent}"""
    jobs = inputs["notify"]
    session = SessionLocal()
    try:
        added = 0
        for job in jobs:
            if session.query(SeenJob).filter_by(job_id=job["id"]).first() is None:
                session.add(SeenJob(job_id=job["id"]))
                added += 1
        session.commit()
        return f"Marked {added} jobs as seen"
    finally:
        session.close()

def save_jobs(inputs: dict, config: dict) -> dict:
    jobs = _all_jobs(inputs)
    if not jobs:
        return {"new": 0, "refreshed": 0, "closed": 0}

    now = datetime.datetime.utcnow()
    unique = {j["id"]: j for j in jobs}
    # only complete company boards can tell us a job has really vanished
    complete_companies = {
        j.get("company", "") for j in unique.values()
        if j.get("source", "greenhouse") in COMPLETE_SOURCES
    }

    with SessionLocal() as session:
        # 1. which of these jobs do we already have?
        stored = {row[0] for row in
                  session.query(Job.job_id).filter(Job.job_id.in_(list(unique)))}

        # 2. add the ones we don't have
        session.add_all([
            Job(job_id=j["id"], title=j["title"], company=j.get("company", ""),
                url=j["url"], location=j["location"],
                source=j.get("source", "greenhouse"), level=j.get("level", ""),
                last_seen=now, is_open=True)
            for j in unique.values() if j["id"] not in stored
        ])

        # 3. refresh the ones we do have
        session.query(Job).filter(Job.job_id.in_(list(stored))).update(
            {"last_seen": now, "is_open": True}, synchronize_session=False)

        # 4. close jobs from complete boards that were not seen this run
        closed = session.query(Job).filter(
            Job.source.in_(list(COMPLETE_SOURCES)),
            Job.company.in_(list(complete_companies)),
            Job.is_open.is_(True),
            Job.last_seen < now,
        ).update({"is_open": False}, synchronize_session=False)

        session.commit()

    return {"new": len(unique) - len(stored), "refreshed": len(stored), "closed": closed}