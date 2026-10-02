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