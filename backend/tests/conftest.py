"""Shared fixtures. If FastAPI isn't installed (e.g. a locked-down sandbox) a tiny stand-in lets the
router *functions* be imported and called directly; with FastAPI installed the real TestClient tests run."""
import sys
import types

import pytest

try:
    import fastapi  # noqa: F401
    HAVE_FASTAPI = True
except ImportError:  # pragma: no cover
    HAVE_FASTAPI = False

    class _HTTPException(Exception):
        def __init__(self, status_code, detail=None):
            self.status_code, self.detail = status_code, detail

    class _Router:
        def __init__(self, prefix="", tags=None):
            self.prefix = prefix

        def _reg(self, *a, **k):
            return lambda fn: fn
        get = post = patch = put = delete = _reg

    mod = types.ModuleType("fastapi")
    mod.APIRouter, mod.HTTPException = _Router, _HTTPException
    mod.Query = lambda default=None, **k: default
    mod.Depends = lambda dep=None: dep
    mod.Header = lambda default=None, **k: default
    mod.FastAPI = object
    sys.modules["fastapi"] = mod

from app.db.repo import SQLiteRepository, set_repo  # noqa: E402


@pytest.fixture()
def repo():
    r = SQLiteRepository(":memory:")
    set_repo(r)
    yield r
    set_repo(None)


@pytest.fixture(scope="session", autouse=True)
def _offline_llm():
    import os
    os.environ["LLM_PROVIDER"] = "offline"


@pytest.fixture(autouse=True)
def _fast_hashing_and_clean_limiter(monkeypatch):
    from app import auth
    monkeypatch.setattr(auth, "PBKDF2_ITERS", 1000)  # real value is 600k; tests only need the logic
    auth._FAILS.clear()


@pytest.fixture()
def make_user(repo):
    """make_user("admin") -> public user dict, created through the real signup route."""
    from app.routers import auth as auth_router
    from app.schemas import SignupRequest
    counter = {"n": 0}

    def _make(role="employee", name=None, email=None):
        counter["n"] += 1
        res = auth_router.signup(SignupRequest(name=name or f"Test {role} {counter['n']}", email=email or f"{role}{counter['n']}@gmail.com",
                                               password="Passw0rd!x", role=role))
        if role != "employee":  # sign-up never grants staff roles; simulate the admin's approval / make_admin script
            repo.update("users", res["user"]["user_id"], {"role": role})
            for r in repo.list("role_requests", {"user_id": res["user"]["user_id"]}):
                repo.update("role_requests", r["request_id"], {"status": "approved"})
        return repo.get("users", res["user"]["user_id"]) and {k: v for k, v in repo.get("users", res["user"]["user_id"]).items() if k != "password_hash"}
    return _make
