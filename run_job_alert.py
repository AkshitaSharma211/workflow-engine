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
    "fetch":    {"deps": [],          "type": "fetch_jobs",     "config": {"board": "stripe"}},
    "filter":   {"deps": ["fetch"],   "type": "filter_jobs",    "config": {"keyword": "machine learning"}},
    "dedupe":   {"deps": ["filter"],  "type": "dedupe",         "config": {}},
    "notify":   {"deps": ["dedupe"],  "type": "telegram_alert", "config": {}},
    "mark": {"deps": ["notify"], "type": "mark_seen", "config": {}},
}    

if __name__ == "__main__":
    results = run_workflow(workflow, REGISTRY)
    print(results)