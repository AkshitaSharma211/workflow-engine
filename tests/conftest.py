import os
import datetime

import pytest
from dotenv import load_dotenv

load_dotenv()

TEST_URL = os.environ.get("TEST_DATABASE_URL")
REAL_URL = os.environ.get("DATABASE_URL")
if not TEST_URL:
    pytest.exit("TEST_DATABASE_URL is not set. Tests must never use the real database.", returncode=2)
if TEST_URL == REAL_URL and os.environ.get("CI") != "true":
    pytest.exit("TEST_DATABASE_URL equals DATABASE_URL. Point it at the test branch.", returncode=2)

os.environ["DATABASE_URL"] = TEST_URL
os.environ.setdefault("SECRET_KEY", "test-secret-key")
os.environ.setdefault("API_KEY", "test-api-key")

from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import text  # noqa: E402


@pytest.fixture(scope="session", autouse=True)
def _create_tables():
    from engine import db
    db.Base.metadata.create_all(db.engine)


@pytest.fixture(autouse=True)
def _clean_database():
    """Every test starts with empty tables."""
    from engine import db
    with db.engine.begin() as conn:
        conn.execute(text(
            "TRUNCATE user_jobs, jobs, users, step_runs, runs, seen_jobs "
            "RESTART IDENTITY CASCADE"))
    yield


@pytest.fixture
def client():
    from api.main import app
    with TestClient(app) as c:
        yield c


@pytest.fixture
def other_client():
    """A second browser, with its own cookies."""
    from api.main import app
    with TestClient(app) as c:
        yield c


@pytest.fixture
def seeded_jobs():
    """Three jobs. Returns {job_id: database row id}."""
    from engine.db import SessionLocal, Job
    now = datetime.datetime.utcnow()
    rows = [
        Job(job_id=1, title="Machine Learning Intern", company="acme",
            url="https://e.com/1", location="Remote",
            first_seen=now, last_seen=now, is_open=True),
        Job(job_id=2, title="Software Engineer, Internal Systems", company="acme",
            url="https://e.com/2", location="Remote",
            first_seen=now, last_seen=now, is_open=True),
        Job(job_id=3, title="Data Analyst", company="globex",
            url="https://e.com/3", location="Berlin",
            first_seen=now, last_seen=now, is_open=True),
    ]
    with SessionLocal() as s:
        s.add_all(rows)
        s.commit()
        return {j.job_id: j.id for j in rows}