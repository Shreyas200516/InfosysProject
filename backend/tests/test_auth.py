import time

import pytest
from pydantic import ValidationError

from app import auth
from app.config import settings
from app.routers import admin as admin_router
from app.routers import auth as auth_router
from app.routers import knowledge, ops, tickets
from app.schemas import AnalyzeRequest, LoginRequest, SearchRequest, SignupRequest, StatusUpdate, TicketCreate

PW = "Passw0rd!x"


def status_of(fn, *a, **k):
    try:
        fn(*a, **k)
    except Exception as e:  # HTTPException (real or shim)
        return getattr(e, "status_code", None)
    return 200


# ---------- passwords & tokens ----------
def test_password_hash_is_salted_and_verifies():
    h1, h2 = auth.hash_password(PW), auth.hash_password(PW)
    assert h1 != h2 and PW not in h1 and h1.startswith("pbkdf2_sha256$")
    assert auth.verify_password(PW, h1) and not auth.verify_password("wrong", h1)
    assert not auth.verify_password(PW, None) and not auth.verify_password(PW, "garbage")


def test_token_roundtrip_tamper_and_expiry(monkeypatch):
    user = {"user_id": "USR-1", "role": "admin"}
    tok = auth.create_token(user)
    assert auth.decode_token(tok)["sub"] == "USR-1"
    head, payload, sig = tok.split(".")
    forged = auth._b64e(b'{"sub":"USR-1","role":"admin","exp":9999999999}')
    for bad in (f"{head}.{forged}.{sig}", f"{head}.{payload}.AAAA", "x.y", ""):
        assert status_of(auth.decode_token, bad) == 401
    monkeypatch.setattr(settings, "token_ttl_hours", -1)
    assert status_of(auth.decode_token, auth.create_token(user)) == 401


def test_token_signed_with_other_secret_rejected(monkeypatch):
    tok = auth.create_token({"user_id": "USR-1", "role": "employee"})
    monkeypatch.setattr(settings, "auth_secret", "a-different-secret")
    assert status_of(auth.decode_token, tok) == 401


# ---------- signup validation ----------
@pytest.mark.parametrize("patch", [{"name": "A"}, {"email": "nope"}, {"password": "short1"}, {"password": "onlyletters"},
                                   {"password": "12345678"}, {"role": "superuser"}])
def test_signup_validation(patch):
    with pytest.raises(ValidationError):
        SignupRequest(**{"name": "Asha Rao", "email": "asha@gmail.com", "password": PW, **patch})


def test_signup_login_me_flow(repo):
    res = auth_router.signup(SignupRequest(name="Asha  Rao", email="Asha@Gmail.com", password=PW, role="employee"))
    assert res["user"]["email"] == "asha@gmail.com" and res["user"]["name"] == "Asha Rao"
    assert "password_hash" not in res["user"] and auth.decode_token(res["token"])["role"] == "employee"
    stored = repo.get("users", res["user"]["user_id"])
    assert stored["password_hash"] and PW not in stored["password_hash"]
    login = auth_router.login(LoginRequest(email="ASHA@gmail.com", password=PW))
    assert login["user"]["user_id"] == res["user"]["user_id"]
    me = auth.current_user(f"Bearer {login['token']}")
    assert me["email"] == "asha@gmail.com" and "password_hash" not in me


def test_duplicate_email_conflict(make_user):
    make_user("employee", email="dup@gmail.com")
    assert status_of(auth_router.signup, SignupRequest(name="Other One", email="DUP@gmail.com", password=PW)) == 409


# ---------- role approval ----------
def _signup(role, email, name="Some One"):
    return auth_router.signup(SignupRequest(name=name, email=email, password=PW, role=role))


def test_signup_never_grants_a_staff_role(repo):
    for role in ("support_engineer", "admin"):
        res = _signup(role, f"{role}@gmail.com")
        assert res["user"]["role"] == "employee" and res["pending_role"] == role
        assert auth.decode_token(res["token"])["role"] == "employee"
        assert repo.get("users", res["user"]["user_id"])["role"] == "employee"
    plain = _signup("employee", "plain@gmail.com")
    assert plain["pending_role"] is None and repo.count("role_requests") == 2


def test_pending_user_cannot_reach_staff_or_admin_endpoints(repo):
    res = _signup("admin", "wannabe@gmail.com")
    me = auth.current_user(f"Bearer {res['token']}")
    assert me["role"] == "employee"
    assert status_of(auth.staff_only, me) == 403 and status_of(auth.admin_only, me) == 403
    # The admin endpoints are protected by Depends(admin_only), which the check above exercises directly.


def test_admins_are_notified_of_a_request(make_user, repo):
    admin = make_user("admin", email="boss@gmail.com")
    _signup("support_engineer", "newhire@gmail.com", "New Hire")
    mail = [n for n in repo.list("notifications") if n["recipient"] == "boss@gmail.com"]
    assert len(mail) == 1 and "New Hire" in mail[0]["subject"] and mail[0]["ticket_id"] is None
    assert admin_router.list_requests("pending", admin)["pending"] == 1


def test_signup_still_works_with_no_admin_yet(repo):
    res = _signup("admin", "first@gmail.com")
    assert res["pending_role"] == "admin" and repo.count("role_requests", {"status": "pending"}) == 1


def test_approve_grants_role_immediately_even_on_existing_token(make_user, repo):
    admin = make_user("admin", email="boss@gmail.com")
    res = _signup("support_engineer", "eng@gmail.com")
    rid = admin_router.list_requests("pending", admin)["items"][0]["request_id"]
    done = admin_router.approve(rid, admin)
    assert done["status"] == "approved" and done["reviewed_by"] == "boss@gmail.com"
    assert auth.current_user(f"Bearer {res['token']}")["role"] == "support_engineer"  # role is re-read from the DB
    assert auth_router.me(auth.current_user(f"Bearer {res['token']}"))["pending_role"] is None
    assert any(n["recipient"] == "eng@gmail.com" and "approved" in n["subject"] for n in repo.list("notifications"))


def test_reject_leaves_employee(make_user, repo):
    admin = make_user("admin", email="boss@gmail.com")
    res = _signup("admin", "greedy@gmail.com")
    rid = admin_router.list_requests("pending", admin)["items"][0]["request_id"]
    assert admin_router.reject(rid, admin)["status"] == "rejected"
    assert repo.get("users", res["user"]["user_id"])["role"] == "employee"
    assert auth.current_user(f"Bearer {res['token']}")["role"] == "employee"
    assert auth_router.login(LoginRequest(email="greedy@gmail.com", password=PW))["pending_role"] is None
    assert any("declined" in n["subject"] for n in repo.list("notifications") if n["recipient"] == "greedy@gmail.com")


def test_a_request_can_only_be_decided_once(make_user):
    admin = make_user("admin", email="boss@gmail.com")
    _signup("support_engineer", "eng@gmail.com")
    rid = admin_router.list_requests("pending", admin)["items"][0]["request_id"]
    admin_router.reject(rid, admin)
    assert status_of(admin_router.approve, rid, admin) == 409 and status_of(admin_router.reject, rid, admin) == 409
    assert status_of(admin_router.approve, "RRQ-nope", admin) == 404


def test_make_admin_script(repo):
    from scripts import make_admin
    assert make_admin.main("ghost@gmail.com") == 1
    res = _signup("admin", "owner@gmail.com")
    assert make_admin.main("OWNER@gmail.com") == 0
    assert repo.get("users", res["user"]["user_id"])["role"] == "admin"
    assert repo.count("role_requests", {"status": "pending"}) == 0


# ---------- login ----------
def test_login_errors_are_uniform_and_throttled(make_user):
    u = make_user("employee", email="who@gmail.com")
    wrong_pw = status_of(auth_router.login, LoginRequest(email="who@gmail.com", password="Wrong1234"))
    no_user = status_of(auth_router.login, LoginRequest(email="ghost@gmail.com", password="Wrong1234"))
    assert wrong_pw == no_user == 401
    for _ in range(auth.MAX_FAILS):
        status_of(auth_router.login, LoginRequest(email="who@gmail.com", password="Wrong1234"))
    assert status_of(auth_router.login, LoginRequest(email="who@gmail.com", password=PW)) == 429  # locked even with the right password


def test_successful_login_clears_failures(make_user):
    make_user("employee", email="ok@gmail.com")
    for _ in range(3):
        status_of(auth_router.login, LoginRequest(email="ok@gmail.com", password="Wrong1234"))
    assert status_of(auth_router.login, LoginRequest(email="ok@gmail.com", password=PW)) == 200
    assert not auth._FAILS.get("ok@gmail.com")


def test_current_user_rejects_bad_headers(make_user):
    assert status_of(auth.current_user, None) == 401
    assert status_of(auth.current_user, "Token abc") == 401
    assert status_of(auth.current_user, "Bearer not.a.token") == 401


def test_deleted_user_token_stops_working(repo, make_user):
    u = make_user()
    tok = auth.create_token(u)
    repo._conn.execute("DELETE FROM users WHERE user_id = ?", (u["user_id"],)); repo._conn.commit()
    assert status_of(auth.current_user, f"Bearer {tok}") == 401


def test_user_without_password_cannot_log_in(repo):
    repo.insert("users", {"user_id": "USR-X", "name": "Seeded", "email": "seeded@gmail.com", "role": "employee", "created_at": "now"})
    assert status_of(auth_router.login, LoginRequest(email="seeded@gmail.com", password="anything1")) == 401


# ---------- role-based access ----------
BODY = dict(subject="VPN keeps disconnecting", description="The VPN drops every ten minutes at home.")


def test_employee_sees_only_own_tickets(make_user):
    a, b = make_user("employee"), make_user("employee")
    ta = tickets.create_ticket(TicketCreate(**BODY), user=a)["ticket"]["ticket_id"]
    tb = tickets.create_ticket(TicketCreate(**{**BODY, "subject": "Printer offline today"}), user=b)["ticket"]["ticket_id"]
    assert [t["ticket_id"] for t in tickets.list_tickets(user=a)["items"]] == [ta]
    assert tickets.get_ticket(ta, user=a)["ticket"]["ticket_id"] == ta
    assert status_of(tickets.get_ticket, tb, user=a) == 404          # same answer as "does not exist"
    eng = make_user("support_engineer")
    assert tickets.list_tickets(user=eng)["total"] == 2 and tickets.get_ticket(tb, user=eng)


def test_ticket_requester_comes_from_signed_in_user(make_user):
    u = make_user("employee", name="Real Person", email="real@gmail.com")
    d = tickets.create_ticket(TicketCreate(**BODY), user=u)
    assert d["user"]["email"] == "real@gmail.com" and "password_hash" not in d["user"]


def test_ticket_detail_never_exposes_password_hash(make_user):
    u = make_user()
    d = tickets.create_ticket(TicketCreate(**BODY), user=u)
    assert "password_hash" not in str(d)


def test_staff_only_endpoints(make_user):
    emp, eng = make_user("employee"), make_user("support_engineer")
    tid = tickets.create_ticket(TicketCreate(**BODY), user=emp)["ticket"]["ticket_id"]
    guard = auth.staff_only
    assert status_of(guard, user=emp) == 403 and status_of(guard, user=eng) == 200
    assert status_of(auth.admin_only, user=eng) == 403 and status_of(auth.admin_only, user=make_user("admin")) == 200
    out = tickets.update_status(tid, StatusUpdate(status="Resolved"), user=eng)
    assert out["ticket"]["status"] == "Resolved" and any("support_engineer" in a["performed_by"] for a in out["activity"])
    assert ops.summary(user=eng)["totals"]["tickets"] == 1
