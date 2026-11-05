"""Promote an existing account to admin. This is how the FIRST admin is created.

    python -m scripts.make_admin you@example.com

Run it on the server after that person has signed up. It needs access to the server's database,
which is exactly why it is safe: nobody can do this from the website.
"""
import sys

from app.db.repo import get_repo, now_iso


def main(email: str) -> int:
    repo = get_repo()
    rows = repo.list("users", {"email": email.strip().lower()}, limit=1)
    if not rows:
        print(f"No account with email {email}. Sign up on the website first, then run this again.")
        return 1
    user = rows[0]
    repo.update("users", user["user_id"], {"role": "admin"})
    for r in repo.list("role_requests", {"user_id": user["user_id"], "status": "pending"}):
        repo.update("role_requests", r["request_id"], {"status": "approved", "reviewed_by": "make_admin script", "reviewed_at": now_iso()})
    print(f"{user['email']} is now an admin.")
    return 0


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("usage: python -m scripts.make_admin EMAIL")
        sys.exit(2)
    sys.exit(main(sys.argv[1]))
