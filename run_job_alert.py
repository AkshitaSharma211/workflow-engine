from engine.executor import run_workflow
from engine.steps import (fetch_jobs, filter_jobs, dedupe, telegram_alert,
                          mark_seen, save_jobs)
from engine.sources import fetch_muse, fetch_remotive, fetch_lever, fetch_ashby

REGISTRY = {
    "fetch_jobs": fetch_jobs,
    "fetch_muse": fetch_muse,
    "fetch_remotive": fetch_remotive,
    "fetch_lever": fetch_lever,
    "fetch_ashby": fetch_ashby,
    "filter_jobs": filter_jobs,
    "dedupe": dedupe,
    "telegram_alert": telegram_alert,
    "mark_seen": mark_seen,
    "save_jobs": save_jobs,
}

FETCH_STEPS = ["fetch", "fetch_muse", "fetch_remotive", "fetch_lever", "fetch_ashby"]

workflow = {
    "fetch": {"deps": [], "type": "fetch_jobs", "config": {"boards": [
        "stripe", "airbnb", "databricks", "cloudflare", "coinbase",
        "anthropic", "scaleai", "postman"]}},
    "fetch_muse": {"deps": [], "type": "fetch_muse", "config": {
        "levels": ["Internship", "Entry Level"], "max_pages": 5}},
    "fetch_remotive": {"deps": [], "type": "fetch_remotive", "config": {}},
    "fetch_lever": {"deps": [], "type": "fetch_lever", "config": {
        "boards": ["spotify", "palantir", "cred", "meesho"]}},
    "fetch_ashby": {"deps": [], "type": "fetch_ashby", "config": {
        "boards": ["openai", "notion", "ramp", "linear", "supabase"]}},

    "filter": {"deps": FETCH_STEPS, "type": "filter_jobs", "config": {
        "keywords": ["machine learning", "ml", "ai", "data", "software", "backend", "engineer"],
        "level_include": ["intern", "interns", "internship", "trainee", "apprentice",
                          "co-op", "junior", "jr", "entry", "graduate", "new grad",
                          "early career", "fresher"],
        "level_exclude": ["senior", "staff", "principal", "lead", "manager"],
        "locations": ["remote", "india", "worldwide", "anywhere"],
        "location_exclude": ["usa only", "us only", "united states", "north america",
                             "canada", "uk only", "europe", "emea"],
    }},
    "dedupe": {"deps": ["filter"], "type": "dedupe", "config": {}},
    "notify": {"deps": ["dedupe"], "type": "telegram_alert", "config": {}},
    "mark": {"deps": ["notify"], "type": "mark_seen", "config": {}},
    "save": {"deps": FETCH_STEPS, "type": "save_jobs", "config": {}},
}

if __name__ == "__main__":
    results = run_workflow(workflow, REGISTRY)
    counts = " ".join(f"{k}={len(results[k])}" for k in FETCH_STEPS)
    print(f"fetched: {counts}")
    print(f"matched={len(results['filter'])} new={len(results['dedupe'])} "
          f"sent={len(results['notify'])}")
    print(f"jobs table: {results['save']}")
    print(results["mark"])