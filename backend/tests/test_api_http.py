"""Real HTTP tests; run only when FastAPI is installed (pip install -r requirements.txt)."""
import pytest

pytest.importorskip("fastapi")
pytest.importorskip("httpx")
from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402


@pytest.fixture()
def client(repo):
    with TestClient(app) as c:
        yield c


def signup(client, role="employee", email="asha@gmail.com"):
    r = client.post("/api/v1/auth/signup", json=dict(name="Asha Rao", email=email, password="Passw0rd!x", role=role))
    assert r.status_code == 201, r.text
    return {"Authorization": f"Bearer {r.json()['token']}"}


def test_health_is_public(client):
    assert client.get("/api/v1/health").json()["status"] == "ok"


def test_endpoints_require_sign_in(client):
    for method, path in [("get", "/api/v1/tickets"), ("get", "/api/v1/analytics/summary"), ("get", "/api/v1/integrations"), ("post", "/api/v1/tickets/analyze")]:
        assert getattr(client, method)(path).status_code == 401, path


def test_signup_login_and_ticket_over_http(client):
    h = signup(client)
    assert client.get("/api/v1/auth/me", headers=h).json()["user"]["email"] == "asha@gmail.com"
    assert client.post("/api/v1/auth/login", json={"email": "asha@gmail.com", "password": "Passw0rd!x"}).status_code == 200
    assert client.post("/api/v1/auth/login", json={"email": "asha@gmail.com", "password": "Wrong12345"}).status_code == 401
    ok = client.post("/api/v1/tickets", headers=h, json=dict(subject="VPN keeps disconnecting", description="The VPN drops every ten minutes."))
    assert ok.status_code == 201 and ok.json()["ticket"]["category"] == "VPN" and "password_hash" not in ok.text
    assert client.post("/api/v1/tickets", headers=h, json={"subject": "x"}).status_code == 422
    assert client.get("/api/v1/tickets/TKT-NOPE", headers=h).status_code == 404


def test_employee_forbidden_from_staff_routes(client):
    emp = signup(client)
    assert client.get("/api/v1/analytics/summary", headers=emp).status_code == 403
    eng = signup(client, role="support_engineer", email="eng@gmail.com")
    assert client.get("/api/v1/analytics/summary", headers=eng).status_code == 200
