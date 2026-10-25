import os
import re
import secrets
import datetime
from pathlib import Path

from fastapi import FastAPI, Depends, Header, HTTPException, BackgroundTasks, Request, Query
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from sqlalchemy import and_, func, or_
from starlette.middleware.sessions import SessionMiddleware

from api.auth import hash_password, verify_password
from engine.db import SessionLocal, Run, StepRun, User, Job, UserJob
from engine.executor import run_workflow
from run_job_alert import workflow, REGISTRY

app = FastAPI()

API_KEY = os.environ.get("API_KEY")
SECRET_KEY = os.environ.get("SECRET_KEY")
if not SECRET_KEY:
    raise RuntimeError("SECRET_KEY is not set")

app.add_middleware(
    SessionMiddleware,
    secret_key=SECRET_KEY,
    same_site="lax",
    https_only=os.environ.get("HTTPS_ONLY", "false") == "true",
    max_age=14 * 24 * 3600,
)

STATIC = Path(__file__).parent / "static"
ASSETS = Path(__file__).parent / "assets"
app.mount("/assets", StaticFiles(directory=ASSETS), name="assets")


# ---------- access checks ----------

def require_api_key(x_api_key: str = Header(None)):
    if not API_KEY or not x_api_key or not secrets.compare_digest(x_api_key, API_KEY):
        raise HTTPException(status_code=401, detail="Invalid or missing API key")


def require_user(request: Request) -> int:
    user_id = request.session.get("user_id")
    if not user_id:
        raise HTTPException(status_code=401, detail="Not logged in")
    return user_id


# ---------- pages ----------

def _page(request: Request, filename: str):
    if not request.session.get("user_id"):
        return RedirectResponse("/login", status_code=302)
    return FileResponse(STATIC / filename)


@app.get("/", include_in_schema=False)
def landing(request: Request):
    if request.session.get("user_id"):
        return RedirectResponse("/dashboard", status_code=302)
    return FileResponse(STATIC / "landing.html")


@app.get("/login", include_in_schema=False)
def login_page(request: Request):
    if request.session.get("user_id"):
        return RedirectResponse("/dashboard", status_code=302)
    return FileResponse(STATIC / "login.html")


@app.get("/signup", include_in_schema=False)
def signup_page(request: Request):
    if request.session.get("user_id"):
        return RedirectResponse("/dashboard", status_code=302)
    return FileResponse(STATIC / "signup.html")


@app.get("/dashboard", include_in_schema=False)
def dashboard_page(request: Request):
    return _page(request, "dashboard.html")


@app.get("/search", include_in_schema=False)
def search_page(request: Request):
    return _page(request, "jobs.html")


@app.get("/my-jobs", include_in_schema=False)
def my_jobs_page(request: Request):
    return _page(request, "my-jobs.html")


@app.get("/activity", include_in_schema=False)
def activity_page(request: Request):
    return _page(request, "activity.html")


# ---------- auth ----------

class Credentials(BaseModel):
    email: str
    password: str


@app.post("/signup", status_code=201)
def signup(creds: Credentials, request: Request):
    email = creds.email.strip().lower()
    if "@" not in email or len(creds.password) < 8:
        raise HTTPException(status_code=422,
                            detail="Valid email and a password of 8+ characters required")
    with SessionLocal() as s:
        if s.query(User).filter(User.email == email).first():
            raise HTTPException(status_code=409, detail="Email already registered")
        user = User(email=email, password_hash=hash_password(creds.password))
        s.add(user)
        s.commit()
        request.session["user_id"] = user.id
    return {"email": email}


@app.post("/login")
def login(creds: Credentials, request: Request):
    email = creds.email.strip().lower()
    with SessionLocal() as s:
        user = s.query(User).filter(User.email == email).first()
        if not user or not verify_password(creds.password, user.password_hash):
            raise HTTPException(status_code=401, detail="Invalid email or password")
        request.session["user_id"] = user.id
    return {"email": email}


@app.post("/logout")
def logout(request: Request):
    request.session.clear()
    return {"status": "logged out"}


@app.get("/me")
def me(request: Request):
    user_id = request.session.get("user_id")
    if not user_id:
        raise HTTPException(status_code=401, detail="Not logged in")
    with SessionLocal() as s:
        user = s.get(User, user_id)
        if not user:
            request.session.clear()
            raise HTTPException(status_code=401, detail="Not logged in")
        return {"id": user.id, "email": user.email}


# ---------- jobs ----------
ENTRY_RE = r"\m(intern|interns|internship|trainee|apprentice|junior|jr|graduate|fresher|entry)\M"
SENIOR_RE = r"\m(senior|sr|staff|principal|lead|manager|director|head|vp)\M"


@app.get("/jobs")
def search_jobs(
    q: str = "",
    company: str = "",
    source: str = "",
    entry: bool = False,
    remote: bool = False,
    days: int = Query(0, ge=0, le=365),
    open_only: bool = True,
    status: str = "",
    page: int = Query(1, ge=1),
    user_id: int = Depends(require_user),
):
    per_page = 25
    with SessionLocal() as s:
        query = s.query(Job)
        if open_only:
            query = query.filter(Job.is_open.is_(True))
        if status:
            query = query.join(
                UserJob, and_(UserJob.job_id == Job.id, UserJob.user_id == user_id)
            ).filter(UserJob.status == status)
        if source:
            query = query.filter(Job.source == source)
        if entry:
            query = query.filter(
                or_(func.lower(func.coalesce(Job.level, "")).in_(["internship", "entry level"]),
                    Job.title.op("~*")(ENTRY_RE)),
                Job.title.op("!~*")(SENIOR_RE),
            )
        if company.strip():
            query = query.filter(Job.company.ilike(f"%{company.strip()}%"))
        if remote:
            query = query.filter(Job.location.ilike("%remote%"))
        if days:
            since = datetime.datetime.utcnow() - datetime.timedelta(days=days)
            query = query.filter(Job.first_seen >= since)
        for word in q.split():
            query = query.filter(Job.title.op("~*")(rf"\m{re.escape(word)}\M"))

        total = query.count()
        jobs = (query.order_by(Job.first_seen.desc(), Job.id.desc())
                     .offset((page - 1) * per_page).limit(per_page).all())

        marks = {
            uj.job_id: uj.status
            for uj in s.query(UserJob).filter(
                UserJob.user_id == user_id, UserJob.job_id.in_([j.id for j in jobs]))
        }
        return {
            "total": total, "page": page, "per_page": per_page,
            "jobs": [
                {"id": j.id, "title": j.title, "company": j.company, "url": j.url,
                 "location": j.location, "first_seen": j.first_seen,
                 "is_open": j.is_open, "my_status": marks.get(j.id),
                 "source": j.source, "level": j.level}
                for j in jobs
            ],
        }

class StatusBody(BaseModel):
    status: str


@app.put("/jobs/{job_id}/status")
def set_status(job_id: int, body: StatusBody, user_id: int = Depends(require_user)):
    if body.status not in {"saved", "applied", "ignored", "none"}:
        raise HTTPException(status_code=422, detail="Invalid status")
    with SessionLocal() as s:
        if not s.get(Job, job_id):
            raise HTTPException(status_code=404, detail="Job not found")
        row = s.query(UserJob).filter_by(user_id=user_id, job_id=job_id).first()
        if body.status == "none":
            if row:
                s.delete(row)
        elif row:
            row.status = body.status
            row.updated_at = datetime.datetime.utcnow()
        else:
            s.add(UserJob(user_id=user_id, job_id=job_id, status=body.status))
        s.commit()
    return {"job_id": job_id, "status": body.status}


@app.get("/stats")
def stats(user_id: int = Depends(require_user)):
    day_ago = datetime.datetime.utcnow() - datetime.timedelta(days=1)
    with SessionLocal() as s:
        open_jobs = s.query(func.count(Job.id)).filter(Job.is_open.is_(True)).scalar()
        new_24h = s.query(func.count(Job.id)).filter(
            Job.is_open.is_(True), Job.first_seen >= day_ago).scalar()
        last_updated = s.query(func.max(Job.last_seen)).scalar()
        mine = dict(
            s.query(UserJob.status, func.count(UserJob.id))
            .filter(UserJob.user_id == user_id)
            .group_by(UserJob.status).all()
        )
        newest = (s.query(Job).filter(Job.is_open.is_(True))
                  .order_by(Job.first_seen.desc(), Job.id.desc()).limit(5).all())
        return {
            "open_jobs": open_jobs,
            "new_24h": new_24h,
            "last_updated": last_updated,
            "mine": {k: mine.get(k, 0) for k in ("saved", "applied", "ignored")},
            "newest": [{"id": j.id, "title": j.title, "company": j.company,
                        "url": j.url, "location": j.location} for j in newest],
        }


# ---------- workflow runs ----------

def _run_in_background():
    try:
        run_workflow(workflow, REGISTRY)
    except Exception as e:
        print(f"background run failed: {e}")


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/workflows", dependencies=[Depends(require_user)])
def list_workflows():
    return [{"name": "job_alert", "steps": list(workflow.keys())}]


@app.post("/workflows/job_alert/run", status_code=202,
          dependencies=[Depends(require_api_key)])
def trigger_job_alert(background_tasks: BackgroundTasks):
    background_tasks.add_task(_run_in_background)
    return {"status": "accepted", "message": "Run started, check /runs"}


@app.get("/runs", dependencies=[Depends(require_user)])
def list_runs(limit: int = Query(10, ge=1, le=100)):
    with SessionLocal() as s:
        runs = s.query(Run).order_by(Run.id.desc()).limit(limit).all()
        return [
            {"id": r.id, "status": r.status,
             "started_at": r.started_at, "finished_at": r.finished_at}
            for r in runs
        ]


@app.get("/runs/{run_id}", dependencies=[Depends(require_user)])
def get_run(run_id: int):
    with SessionLocal() as s:
        steps = s.query(StepRun).filter(StepRun.run_id == run_id).all()
        if not steps:
            raise HTTPException(status_code=404, detail="Run not found")
        return [{"step_id": st.step_id, "status": st.status, "output": st.output}
                for st in steps]