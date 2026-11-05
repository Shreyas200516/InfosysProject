"""Admin-only: approve or reject requests for support-engineer / admin access."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query

from ..auth import admin_only
from ..db.repo import get_repo, now_iso, public_user
from ..integrations.notifier import Notifier

router = APIRouter(prefix="/api/v1/admin", tags=["admin"])


def _with_user(repo, req: dict) -> dict:
    u = public_user(repo.get("users", req["user_id"])) or {}
    return {**req, "name": u.get("name"), "email": u.get("email"), "current_role": u.get("role")}


@router.get("/role-requests")
def list_requests(status: str = Query("pending", pattern="^(pending|approved|rejected|all)$"), admin=Depends(admin_only)):
    repo = get_repo()
    rows = repo.list("role_requests", None if status == "all" else {"status": status}, order_by="created_at", limit=200)
    return {"items": [_with_user(repo, r) for r in rows], "pending": repo.count("role_requests", {"status": "pending"})}


def _decide(request_id: str, approve: bool, admin: dict) -> dict:
    repo = get_repo()
    req = repo.get("role_requests", request_id)
    if not req:
        raise HTTPException(404, "Request not found.")
    if req["status"] != "pending":
        raise HTTPException(409, f"This request was already {req['status']}.")
    user = repo.get("users", req["user_id"])
    if not user:
        raise HTTPException(404, "The user no longer exists.")
    if approve:
        repo.update("users", user["user_id"], {"role": req["requested_role"]})
    # Rejected: nothing to change. The account has been an employee account since sign-up.
    req = repo.update("role_requests", request_id, {"status": "approved" if approve else "rejected",
                                                    "reviewed_by": admin["email"], "reviewed_at": now_iso()})
    try:
        Notifier(repo).role_decided(user["email"], req["requested_role"], approve)
    except Exception:
        pass
    return _with_user(repo, req)


@router.post("/role-requests/{request_id}/approve")
def approve(request_id: str, admin=Depends(admin_only)):
    return _decide(request_id, True, admin)


@router.post("/role-requests/{request_id}/reject")
def reject(request_id: str, admin=Depends(admin_only)):
    return _decide(request_id, False, admin)
