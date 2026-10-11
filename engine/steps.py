import requests
from engine.db import SessionLocal, SeenJob
import os
from dotenv import load_dotenv

load_dotenv()

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
            })

    if failed == len(boards):
        raise RuntimeError("fetch_jobs: every board failed")

    print(f"fetch_jobs: {len(simplified)} jobs from {len(boards) - failed}/{len(boards)} boards")
    return simplified

def filter_jobs(inputs: dict, config: dict) -> list:
    """
    inputs: {"fetch": [list of jobs from fetch_jobs]}
    config: {"keyword": "intern"}
    Returns only jobs whose title contains the keyword (case-insensitive).
    """
    jobs = inputs["fetch"]
    keyword = config["keyword"].lower()

    filtered = []
    for job in jobs:
        if keyword in job["title"].lower():
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