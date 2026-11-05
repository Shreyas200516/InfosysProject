from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from ..auth import check_rate_limit, clear_failures, create_token, current_user, hash_password, record_failure, verify_password, _DUMMY_HASH, STAFF
from ..integrations.notifier import Notifier
from ..db.repo import get_repo, new_id, now_iso, public_user
from ..schemas import LoginRequest, SignupRequest

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


@router.post("/signup", status_code=201)
def signup(body: SignupRequest):
    repo = get_repo()
    email = body.email.lower()
    if repo.list("users", {"email": email}, limit=1):
        raise HTTPException(409, "An account with this email already exists. Sign in instead.")
    # Everyone starts as an employee, whatever they picked. Staff roles are only granted by an admin.
    try:
        user = repo.insert("users", {"user_id": new_id("USR"), "name": body.name, "email": email, "department": None,
                                     "role": "employee", "password_hash": hash_password(body.password), "created_at": now_iso()})
    except Exception as exc:  # unique-constraint race
        raise HTTPException(409, "An account with this email already exists. Sign in instead.") from exc
    pending = None
    if body.role in STAFF:
        repo.insert("role_requests", {"request_id": new_id("RRQ"), "user_id": user["user_id"], "requested_role": body.role,
                                      "status": "pending", "reviewed_by": None, "created_at": now_iso(), "reviewed_at": None})
        pending = body.role
        notifier = Notifier(repo)
        for admin in repo.list("users", {"role": "admin"}, limit=50):
            try:
                notifier.role_requested(admin["email"], user, body.role)
            except Exception:  # a mail problem must never block sign-up; the request is still visible in Approvals
                pass
    return {"token": create_token(user), "user": public_user(user), "pending_role": pending}


@router.post("/login")
def login(body: LoginRequest):
    repo = get_repo()
    email = body.email.lower()
    check_rate_limit(email)
    rows = repo.list("users", {"email": email}, limit=1)
    user = rows[0] if rows else None
    stored = user.get("password_hash") if user else None
    ok = verify_password(body.password, stored or _DUMMY_HASH) and bool(stored)
    if not ok:
        record_failure(email)
        raise HTTPException(401, "Invalid email or password.")
    clear_failures(email)
    return {"token": create_token(user), "user": public_user(user), "pending_role": pending_role(repo, user["user_id"])}


def pending_role(repo, user_id: str):
    rows = repo.list("role_requests", {"user_id": user_id, "status": "pending"}, limit=1)
    return rows[0]["requested_role"] if rows else None


@router.get("/me")
def me(user=Depends(current_user)):
    return {"user": user, "pending_role": pending_role(get_repo(), user["user_id"])}
