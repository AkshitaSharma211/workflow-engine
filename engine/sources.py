import hashlib
import requests

HEADERS = {"User-Agent": "workflow-engine-job-collector/1.0"}
TIMEOUT = 30


def stable_id(source: str, external_id) -> int:
    """A number that is always the same for the same source + id (fits in BIGINT)."""
    digest = hashlib.sha1(f"{source}:{external_id}".encode()).hexdigest()
    return int(digest[:15], 16)


def _get_json(url, params=None):
    r = requests.get(url, params=params, headers=HEADERS, timeout=TIMEOUT)
    r.raise_for_status()
    return r.json()


def fetch_muse(inputs: dict, config: dict) -> list:
    """The Muse: filtered by level, so it returns internships and entry-level roles."""
    levels = config.get("levels", ["Internship", "Entry Level"])
    categories = config.get("categories", [])
    max_pages = config.get("max_pages", 5)
    jobs = []
    try:
        for page in range(max_pages):
            params = [("page", page)] + [("level", l) for l in levels] \
                     + [("category", c) for c in categories]
            data = _get_json("https://www.themuse.com/api/public/jobs", params)
            for r in data.get("results", []):
                where = ", ".join(l.get("name", "") for l in r.get("locations", [])) or "Unknown"
                level = ((r.get("levels") or [{}])[0]).get("name", "")
                jobs.append({
                    "id": stable_id("muse", r["id"]),
                    "title": r.get("name", ""),
                    "url": (r.get("refs") or {}).get("landing_page", ""),
                    "location": where,
                    "company": (r.get("company") or {}).get("name", "muse"),
                    "source": "muse",
                    "level": level,
                })
            if page + 1 >= data.get("page_count", 0):
                break
    except Exception as e:
        print(f"fetch_muse: stopped early ({e})")
    print(f"fetch_muse: {len(jobs)} jobs")
    return jobs


def fetch_remotive(inputs: dict, config: dict) -> list:
    """Remotive: one request per run (its terms limit how often you may fetch)."""
    words = config.get("category_words", ["software", "data", "dev", "machine", "ai", "engineer"])
    jobs = []
    try:
        data = _get_json("https://remotive.com/api/remote-jobs")
        for r in data.get("jobs", []):
            category = (r.get("category") or "").lower()
            if not any(w in category for w in words):
                continue
            where = r.get("candidate_required_location") or "Worldwide"
            jobs.append({
                "id": stable_id("remotive", r["id"]),
                "title": r.get("title", ""),
                "url": r.get("url", ""),
                "location": f"Remote - {where}",
                "company": r.get("company_name", "remotive"),
                "source": "remotive",
                "level": "",
            })
    except Exception as e:
        print(f"fetch_remotive: failed ({e})")
    print(f"fetch_remotive: {len(jobs)} jobs")
    return jobs


def fetch_lever(inputs: dict, config: dict) -> list:
    boards = config.get("boards", [])
    jobs, loaded = [], 0
    for board in boards:
        try:
            data = _get_json(f"https://api.lever.co/v0/postings/{board}", {"mode": "json"})
        except Exception as e:
            print(f"fetch_lever: skipping '{board}': {e}")
            continue
        loaded += 1
        for r in data:
            cats = r.get("categories") or {}
            where = cats.get("location") or "Unknown"
            if (r.get("workplaceType") or "").lower() == "remote" and "remote" not in where.lower():
                where = f"Remote - {where}"
            level = "Internship" if "intern" in (cats.get("commitment") or "").lower() else ""
            jobs.append({
                "id": stable_id("lever", r["id"]),
                "title": r.get("text", ""),
                "url": r.get("hostedUrl", ""),
                "location": where,
                "company": board,
                "source": "lever",
                "level": level,
            })
    print(f"fetch_lever: {len(jobs)} jobs from {loaded}/{len(boards)} boards")
    return jobs


def fetch_ashby(inputs: dict, config: dict) -> list:
    boards = config.get("boards", [])
    jobs, loaded = [], 0
    for board in boards:
        try:
            data = _get_json(f"https://api.ashbyhq.com/posting-api/job-board/{board}")
        except Exception as e:
            print(f"fetch_ashby: skipping '{board}': {e}")
            continue
        loaded += 1
        for r in data.get("jobs", []):
            if r.get("isListed") is False:
                continue
            where = r.get("location") or "Unknown"
            if r.get("isRemote") and "remote" not in where.lower():
                where = f"Remote - {where}"
            level = "Internship" if "intern" in (r.get("employmentType") or "").lower() else ""
            jobs.append({
                "id": stable_id("ashby", r["id"]),
                "title": r.get("title", ""),
                "url": r.get("jobUrl") or r.get("applyUrl") or "",
                "location": where,
                "company": board,
                "source": "ashby",
                "level": level,
            })
    print(f"fetch_ashby: {len(jobs)} jobs from {loaded}/{len(boards)} boards")
    return jobs