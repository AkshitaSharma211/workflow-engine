import pytest
import requests
from unittest.mock import patch, MagicMock
from engine.steps import telegram_alert


def make_jobs(n):
    return [
        {"id": i, "title": f"ML Intern {i}", "url": f"https://example.com/{i}", "location": "Remote"}
        for i in range(n)
    ]


def test_alert_returns_only_jobs_it_sent(monkeypatch):
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "fake-token")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "12345")
    jobs = make_jobs(25)

    with patch("engine.steps.requests.post") as mock_post:
        mock_post.return_value = MagicMock()
        sent = telegram_alert({"dedupe": jobs}, {"max_jobs": 10})

    assert len(sent) == 10
    assert [j["id"] for j in sent] == list(range(10))
    mock_post.assert_called_once()


def test_alert_raises_when_send_fails(monkeypatch):
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "fake-token")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "12345")

    with patch("engine.steps.requests.post") as mock_post:
        mock_post.return_value.raise_for_status.side_effect = requests.HTTPError("boom")
        with pytest.raises(requests.HTTPError):
            telegram_alert({"dedupe": make_jobs(3)}, {"max_jobs": 10})