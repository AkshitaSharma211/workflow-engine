import requests


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