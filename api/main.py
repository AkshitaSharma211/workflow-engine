import os
import secrets
from fastapi import FastAPI, Depends, Header, HTTPException, BackgroundTasks
from engine.db import SessionLocal, Run, StepRun
from engine.executor import run_workflow
from run_job_alert import workflow, REGISTRY

app = FastAPI()
API_KEY = os.environ.get("API_KEY")


def require_api_key(x_api_key: str = Header(None)):
    if not API_KEY or not x_api_key or not secrets.compare_digest(x_api_key, API_KEY):
        raise HTTPException(status_code=401, detail="Invalid or missing API key")


def _run_in_background():
    try:
        run_workflow(workflow, REGISTRY)
    except Exception as e:
        print(f"background run failed: {e}")


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/workflows", dependencies=[Depends(require_api_key)])
def list_workflows():
    return [{"name": "job_alert", "steps": list(workflow.keys())}]


@app.post("/workflows/job_alert/run", status_code=202,
          dependencies=[Depends(require_api_key)])
def trigger_job_alert(background_tasks: BackgroundTasks):
    background_tasks.add_task(_run_in_background)
    return {"status": "accepted", "message": "Run started, check /runs"}


@app.get("/runs", dependencies=[Depends(require_api_key)])
def list_runs(limit: int = 10):
    with SessionLocal() as s:
        runs = s.query(Run).order_by(Run.id.desc()).limit(limit).all()
        return [
            {"id": r.id, "status": r.status,
             "started_at": r.started_at, "finished_at": r.finished_at}
            for r in runs
        ]


@app.get("/runs/{run_id}", dependencies=[Depends(require_api_key)])
def get_run(run_id: int):
    with SessionLocal() as s:
        steps = s.query(StepRun).filter(______).all()      # 1: filter by this run's id
        if not steps:
            raise HTTPException(status_code=____, detail="Run not found")   # 2: which status code?
        return [
            {"step_id": st.step_id, "status": st.status, "output": st.output}
            for st in steps
        ]