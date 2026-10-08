from engine.db import SessionLocal, SeenJob
from engine.steps import (
    fetch_jobs,
    filter_jobs,
    dedupe,
    telegram_alert,
    mark_seen,
)


class FakeResponse:
    """Stand-in for a requests response, so tests don't hit real APIs."""

    def __init__(self, json_data=None):
        self._json = json_data

    def raise_for_status(self):
        pass

    def json(self):
        return self._json


def clear_seen_jobs():
    session = SessionLocal()
    session.query(SeenJob).delete()
    session.commit()
    session.close()


# ---------- fetch_jobs ----------

def test_fetch_jobs_returns_real_data():
    # Real network call to Greenhouse
    result = fetch_jobs({}, {"board": "stripe"})
    assert isinstance(result, list)
    assert len(result) > 0
    assert "title" in result[0]
    assert "url" in result[0]


def test_fetch_jobs_handles_missing_location(monkeypatch):
    # Needs the location guard in fetch_jobs:
    #   location = (job.get("location") or {}).get("name", "Unknown")
    fake_data = {
        "jobs": [
            {"id": 1, "title": "No Location Job", "absolute_url": "u", "location": None},
            {"id": 2, "title": "Normal Job", "absolute_url": "v", "location": {"name": "Pune"}},
        ]
    }
    monkeypatch.setattr(
        "engine.steps.requests.get", lambda *a, **k: FakeResponse(fake_data)
    )
    result = fetch_jobs({}, {"board": "anything"})
    assert result[0]["location"] == "Unknown"
    assert result[1]["location"]