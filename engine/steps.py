import requests
from engine.db import SessionLocal, SeenJob
import os
from dotenv import load_dotenv

load_dotenv()



def fetch_jobs(inputs: dict, config: dict) -> list:
    """
    config: {"board": "stripe"}
    Returns a list of simplified job dicts.
    """
    board = config["board"]
    url = f"https://boards-api.greenhouse.io/v1/boards/{board}/jobs"

    response = requests.get(url)
    response.raise_for_status()  # raises an error if the request failed

    data = response.json()
    jobs = data["jobs"]

    simplified = []
    for job in jobs:
        simplified.append({
            "id": job["id"],
            "title": job["title"],
            "url": job["absolute_url"],
            "location": job["location"]["name"],
        })

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

    new_jobs = []
    for job in jobs:
        already_seen = session.query(SeenJob).filter_by(job_id=job["id"]).first()
        if already_seen is None:
            new_jobs.append(job)

    session.close()
    return new_jobs


def telegram_alert(inputs: dict, config: dict) -> str:
    """
    inputs: {"dedupe": [list of new jobs]}
    Sends a Telegram message listing the new jobs.
    """
    jobs = inputs["dedupe"]
    if not jobs:
        return "No new jobs, nothing sent"

    lines = [f"{job['title']} ({job['location']}) - {job['url']}" for job in jobs]
    message = "New jobs found:\n" + "\n".join(lines)

    token = os.environ["TELEGRAM_BOT_TOKEN"]
    chat_id = os.environ["TELEGRAM_CHAT_ID"]
    url = f"https://api.telegram.org/bot{token}/sendMessage"

    response = requests.post(url, data={"chat_id": chat_id, "text": message})
    response.raise_for_status()
    return "Message sent"