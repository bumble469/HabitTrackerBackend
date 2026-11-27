from datetime import date, timedelta

DAY = timedelta(days=1)


def register(client, email="ann@example.com", password="secret123", tz="Asia/Kolkata"):
    r = client.post(
        "/api/auth/register",
        json={"email": email, "password": password, "display_name": "Ann", "timezone": tz},
    )
    assert r.status_code == 201, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def make_habit(client, headers, name="Read", days_old=0):
    body = {"name": name, "created_on": (date.today() - days_old * DAY).isoformat()}
    r = client.post("/api/habits", json=body, headers=headers)
    assert r.status_code == 201, r.text
    return r.json()


def tick(client, headers, habit_id, days_ago):
    day = (date.today() - days_ago * DAY).isoformat()
    r = client.put(f"/api/habits/{habit_id}/completions/{day}", headers=headers)
    assert r.status_code == 204, r.text
    return day


# ---------- meta ----------

def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_habits_require_login(client):
    assert client.get("/api/habits").status_code == 401
    bad = {"Authorization": "Bearer not-a-real-token"}
    assert client.get("/api/habits", headers=bad).status_code == 401


# ---------- auth ----------

def test_register_login_and_me(client):
    headers = register(client)
    me = client.get("/api/auth/me", headers=headers)
    assert me.status_code == 200
    assert me.json()["email"] == "ann@example.com"
    assert me.json()["ai_enabled"] is True

    dup = client.post("/api/auth/register", json={"email": "ANN@example.com", "password": "secret123"})
    assert dup.status_code == 409

    bad = client.post("/api/auth/login", json={"email": "ann@example.com", "password": "wrong-password"})
    assert bad.status_code == 401
    ok = client.post("/api/auth/login", json={"email": "Ann@Example.com", "password": "secret123"})
    assert ok.status_code == 200
    assert ok.json()["access_token"]


def test_register_validation(client):
    short = client.post("/api/auth/register", json={"email": "a@b.com", "password": "short"})
    assert short.status_code == 422
    bad_email = client.post("/api/auth/register", json={"email": "nope", "password": "secret123"})
    assert bad_email.status_code == 422


# ---------- habits ----------

def test_habit_crud_archive_and_restore(client):
    a = register(client)
    habit = make_habit(client, a, "  Read  ")
    assert habit["name"] == "Read"
    assert habit["archived_at"] is None

    patched = client.patch(f"/api/habits/{habit['id']}", json={"description": "20 pages"}, headers=a)
    assert patched.status_code == 200
    assert patched.json()["description"] == "20 pages"

    assert client.delete(f"/api/habits/{habit['id']}", headers=a).status_code == 204
    assert client.get("/api/habits", headers=a).json() == []
    archived = client.get("/api/habits?include_archived=true", headers=a).json()
    assert len(archived) == 1 and archived[0]["archived_at"] is not None
    assert client.get(f"/api/habits/{habit['id']}", headers=a).status_code == 404

    restored = client.post(f"/api/habits/{habit['id']}/restore", headers=a)
    assert restored.status_code == 200
    assert restored.json()["archived_at"] is None
    assert len(client.get("/api/habits", headers=a).json()) == 1


def test_permanent_delete(client):
    a = register(client)
    habit = make_habit(client, a)
    assert client.delete(f"/api/habits/{habit['id']}?permanent=true", headers=a).status_code == 204
    assert client.get("/api/habits?include_archived=true", headers=a).json() == []


def test_users_cannot_see_each_others_habits(client):
    a = register(client, "a@example.com")
    b = register(client, "b@example.com")
    habit = make_habit(client, a)
    assert client.get(f"/api/habits/{habit['id']}", headers=b).status_code == 404
    assert client.delete(f"/api/habits/{habit['id']}", headers=b).status_code == 404
    assert client.get("/api/habits", headers=b).json() == []


# ---------- check-ins ----------

def test_check_in_cycle(client):
    a = register(client)
    habit = make_habit(client, a)
    yesterday = tick(client, a, habit["id"], 1)
    tick(client, a, habit["id"], 1)  # twice is fine
    assert client.get(f"/api/habits/{habit['id']}/completions", headers=a).json() == [yesterday]
    assert client.get("/api/completions", headers=a).json() == {habit["id"]: [yesterday]}

    url = f"/api/habits/{habit['id']}/completions/{yesterday}"
    assert client.delete(url, headers=a).status_code == 204
    assert client.get(f"/api/habits/{habit['id']}/completions", headers=a).json() == []

    future = (date.today() + 5 * DAY).isoformat()
    r = client.put(f"/api/habits/{habit['id']}/completions/{future}", headers=a)
    assert r.status_code == 422


# ---------- risk ----------

def test_risk_from_database_and_history(client):
    a = register(client)
    old = make_habit(client, a, "Gym", days_old=60)
    new = make_habit(client, a, "New", days_old=0)
    for back in (1, 2, 3, 10, 11):
        tick(client, a, old["id"], back)

    r = client.get("/api/risk", headers=a)
    assert r.status_code in (200, 503)  # 503 only if the model has not been trained yet
    if r.status_code == 200:
        by_id = {x["habit_id"]: x for x in r.json()}
        assert by_id[old["id"]]["level"] in {"low", "medium", "high"}
        assert 0 <= by_id[old["id"]]["risk"] <= 1
        assert by_id[new["id"]]["level"] == "not_enough_data"
        assert by_id[new["id"]]["risk"] is None
        history = client.get(f"/api/habits/{old['id']}/risk/history", headers=a)
        assert history.status_code == 200
        assert len(history.json()) == 1


def test_stateless_risk_endpoint_returns_valid_scores(client):
    body = {
        "today": "2026-11-21",
        "habits": [{"id": "h1", "name": "Gym", "createdAt": "2026-10-01"}],
        "completions": {"h1": ["2026-11-01", "2026-11-02", "2026-11-14", "2026-11-15"]},
    }
    r = client.post("/api/risk", json=body)
    assert r.status_code in (200, 503)
    if r.status_code == 200:
        item = r.json()[0]
        assert item["habit_id"] == "h1"
        assert 0 <= item["risk"] <= 1
        assert item["level"] in {"low", "medium", "high"}


def test_stateless_risk_endpoint_rejects_bad_input(client):
    r = client.post("/api/risk", json={"habits": [{"id": "h1"}]})  # missing created date
    assert r.status_code == 422


# ---------- AI toggle ----------

def test_ai_toggle_blocks_ai_routes(client):
    a = register(client)
    r = client.patch("/api/auth/me", json={"ai_enabled": False}, headers=a)
    assert r.status_code == 200 and r.json()["ai_enabled"] is False

    assert client.get("/api/risk", headers=a).status_code == 403

    client.patch("/api/auth/me", json={"ai_enabled": True}, headers=a)
    assert client.get("/api/risk", headers=a).status_code in (200, 503)


# ---------- export / import ----------

def test_export_and_import_round_trip(client):
    a = register(client, "a@example.com")
    b = register(client, "b@example.com")
    habit = make_habit(client, a, "Read", days_old=10)
    tick(client, a, habit["id"], 1)
    tick(client, a, habit["id"], 2)

    exported = client.get("/api/export", headers=a)
    assert exported.status_code == 200
    payload = exported.json()
    assert len(payload["habits"]) == 1
    assert len(payload["habits"][0]["completed_dates"]) == 2

    imported = client.post("/api/import", json={"habits": payload["habits"]}, headers=b)
    assert imported.status_code == 201
    assert imported.json() == {"habits_created": 1, "completions_created": 2}
    b_habits = client.get("/api/habits", headers=b).json()
    assert [h["name"] for h in b_habits] == ["Read"]
    assert len(client.get("/api/completions", headers=b).json()[b_habits[0]["id"]]) == 2


