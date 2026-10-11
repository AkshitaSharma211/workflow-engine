import os
import secrets
from fastapi import FastAPI, Depends, Header, HTTPException
from engine.db import SessionLocal, Run

app = FastAPI()
API_KEY = os.environ.get("API_KEY")


def require_api_key(x_api_key: str = Header(None)):
    if not API_KEY or not x_api_key or not secrets.compare_digest(x_api_key, API_KEY):
        raise HTTPException(status_code=401, detail="Invalid or missing API key")


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/runs", dependencies=[Depends(require_api_key)])
def list_runs(limit: int = 10):
    with SessionLocal() as s:
        runs = s.query(Run).order_by(Run.id.desc()).limit(limit).all()
        return [
            {"id": r.id, "status": r.status,
             "started_at": r.started_at, "finished_at": r.finished_at}
            for r in runs
        ]