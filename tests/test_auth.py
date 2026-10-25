def signup(client, email="a@example.com", password="password123"):
    return client.post("/signup", json={"email": email, "password": password})


def test_signup_creates_account_and_logs_in(client):
    assert signup(client).status_code == 201
    me = client.get("/me")
    assert me.status_code == 200
    assert me.json()["email"] == "a@example.com"


def test_signup_duplicate_email_rejected(client, other_client):
    signup(client)
    assert signup(other_client).status_code == 409


def test_signup_rejects_short_password(client):
    assert signup(client, password="short").status_code == 422


def test_signup_email_is_case_insensitive(client, other_client):
    signup(client, email="A@Example.com")
    assert signup(other_client, email="a@example.com").status_code == 409


def test_login_with_right_password(client):
    signup(client)
    client.post("/logout")
    r = client.post("/login", json={"email": "a@example.com", "password": "password123"})
    assert r.status_code == 200
    assert client.get("/me").status_code == 200


def test_login_with_wrong_password_rejected(client):
    signup(client)
    client.post("/logout")
    r = client.post("/login", json={"email": "a@example.com", "password": "wrong-password"})
    assert r.status_code == 401


def test_unknown_email_and_wrong_password_look_identical(client):
    signup(client)
    client.post("/logout")
    unknown = client.post("/login", json={"email": "nobody@example.com", "password": "password123"})
    wrong = client.post("/login", json={"email": "a@example.com", "password": "wrong-password"})
    assert unknown.status_code == wrong.status_code == 401
    assert unknown.json() == wrong.json()


def test_logout_ends_the_session(client):
    signup(client)
    client.post("/logout")
    assert client.get("/me").status_code == 401


def test_protected_endpoints_need_login(client):
    for path in ["/jobs", "/stats", "/runs", "/workflows"]:
        assert client.get(path).status_code == 401, path


def test_pages_redirect_to_login_when_logged_out(client):
    for path in ["/dashboard", "/search", "/my-jobs", "/activity"]:
        r = client.get(path, follow_redirects=False)
        assert r.status_code == 302, path
        assert r.headers["location"] == "/login"


def test_trigger_endpoint_needs_the_api_key(client):
    assert client.post("/workflows/job_alert/run").status_code == 401