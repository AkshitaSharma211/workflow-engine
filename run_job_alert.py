from engine.executor import run_workflow
from engine.steps import fetch_jobs, filter_jobs, dedupe, telegram_alert, mark_seen

REGISTRY = {
    "fetch_jobs": fetch_jobs,
    "filter_jobs": filter_jobs,
    "dedupe": dedupe,
    "telegram_alert": telegram_alert,
    "mark_seen": mark_seen,
}

workflow = {
    "fetch": {"deps": [], "type": "fetch_jobs", "config": {"boards": ["stripe", "airbnb", "databricks", "cloudflare", "coinbase"]}},
    "filter": {"deps": ["fetch"], "type": "filter_jobs", "config": {
    "keywords": ["machine learning", "ml", "ai", "data", "software", "backend"],
    "level_include": ["intern", "junior", "entry", "graduate"],
    "level_exclude": ["senior", "staff", "principal", "lead", "manager"],
    "locations": ["remote", "india", "worldwide", "anywhere"],
}},
    "dedupe":   {"deps": ["filter"],  "type": "dedupe",         "config": {}},
    "notify":   {"deps": ["dedupe"],  "type": "telegram_alert", "config": {}},
    "mark": {"deps": ["notify"], "type": "mark_seen", "config": {}},
}    

if __name__ == "__main__":
    results = run_workflow(workflow, REGISTRY)
    print(f"fetched={len(results['fetch'])} matched={len(results['filter'])} "
          f"new={len(results['dedupe'])} sent={len(results['notify'])}")
    print(results["mark"])