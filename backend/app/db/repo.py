"""
Storage layer. One tiny generic interface with two backends:
  * SQLiteRepository   - local dev, tests, and the Milestone-1 spec ("store in SQLite")
  * SupabaseRepository - production (Postgres via supabase-py); schema in supabase/migrations
Both expose: insert / get / update / list / count, keyed by each table's primary key.
"""
from __future__ import annotations

import json
import sqlite3
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional, Protocol

PRIMARY_KEYS = {
    "users": "user_id", "tickets": "ticket_id", "ticket_responses": "response_id",
    "knowledge_base": "article_id", "escalations": "escalation_id", "jira_tickets": "jira_id",
    "activity_logs": "log_id", "agent_runs": "run_id", "notifications": "notification_id", "role_requests": "request_id",
}
JSON_COLUMNS = {
    "ticket_responses": {"steps", "sources", "retrieved"},
    "activity_logs": {"details"}, "agent_runs": {"input", "output"},
}
BOOL_COLUMNS = {"ticket_responses": {"grounded"}}

SQLITE_SCHEMA = """
CREATE TABLE IF NOT EXISTS users (user_id TEXT PRIMARY KEY, name TEXT, email TEXT UNIQUE, department TEXT, role TEXT DEFAULT 'employee', password_hash TEXT, created_at TEXT);
CREATE TABLE IF NOT EXISTS tickets (ticket_id TEXT PRIMARY KEY, user_id TEXT, subject TEXT NOT NULL, description TEXT NOT NULL, ticket_text TEXT,
  category TEXT, category_confidence REAL, priority TEXT, priority_confidence REAL, severity TEXT, severity_score INTEGER,
  business_impact TEXT, affected_users INTEGER, service_tier TEXT, sla_response TEXT, sla_resolution TEXT,
  status TEXT DEFAULT 'New', source TEXT DEFAULT 'portal', resolution_type TEXT, created_at TEXT, updated_at TEXT, resolved_at TEXT);
CREATE TABLE IF NOT EXISTS ticket_responses (response_id TEXT PRIMARY KEY, ticket_id TEXT, generated_response TEXT, steps TEXT, sources TEXT, retrieved TEXT,
  confidence_score REAL, grounded INTEGER, provider TEXT, model TEXT, processing_time_ms REAL, generated_at TEXT);
CREATE TABLE IF NOT EXISTS knowledge_base (article_id TEXT PRIMARY KEY, title TEXT, content TEXT, category TEXT, source TEXT, embedding_id TEXT, created_at TEXT);
CREATE TABLE IF NOT EXISTS escalations (escalation_id TEXT PRIMARY KEY, ticket_id TEXT, assigned_team TEXT, escalation_reason TEXT, status TEXT DEFAULT 'Open', priority TEXT, created_at TEXT);
CREATE TABLE IF NOT EXISTS jira_tickets (jira_id TEXT PRIMARY KEY, ticket_id TEXT, jira_issue_key TEXT, jira_status TEXT, jira_url TEXT, mode TEXT, last_updated TEXT);
CREATE TABLE IF NOT EXISTS activity_logs (log_id TEXT PRIMARY KEY, ticket_id TEXT, action TEXT, performed_by TEXT, details TEXT, timestamp TEXT);
CREATE TABLE IF NOT EXISTS agent_runs (run_id TEXT PRIMARY KEY, ticket_id TEXT, agent_name TEXT, status TEXT, input TEXT, output TEXT, duration_ms REAL, started_at TEXT);
CREATE TABLE IF NOT EXISTS role_requests (request_id TEXT PRIMARY KEY, user_id TEXT, requested_role TEXT, status TEXT DEFAULT 'pending', reviewed_by TEXT, created_at TEXT, reviewed_at TEXT);
CREATE TABLE IF NOT EXISTS notifications (notification_id TEXT PRIMARY KEY, ticket_id TEXT, recipient TEXT, subject TEXT, body TEXT, channel TEXT, status TEXT, created_at TEXT);
CREATE INDEX IF NOT EXISTS idx_tickets_status ON tickets(status);
CREATE INDEX IF NOT EXISTS idx_tickets_created ON tickets(created_at);
CREATE INDEX IF NOT EXISTS idx_logs_ticket ON activity_logs(ticket_id);
"""


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def public_user(user: Optional[dict[str, Any]]) -> Optional[dict[str, Any]]:
    """A user record that is safe to send to a client (never includes the password hash)."""
    if not user:
        return None
    return {k: v for k, v in user.items() if k != "password_hash"}


def new_id(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:8].upper()}"


def new_ticket_id() -> str:
    """Human-friendly unique ticket id, e.g. TKT-20261105-3F9A1C."""
    return f"TKT-{datetime.now(timezone.utc):%Y%m%d}-{uuid.uuid4().hex[:6].upper()}"


class Repository(Protocol):
    backend: str
    def insert(self, table: str, row: dict[str, Any]) -> dict[str, Any]: ...
    def get(self, table: str, key: str) -> Optional[dict[str, Any]]: ...
    def update(self, table: str, key: str, patch: dict[str, Any]) -> Optional[dict[str, Any]]: ...
    def list(self, table: str, where: Optional[dict[str, Any]] = None, order_by: Optional[str] = None,
             desc: bool = True, limit: Optional[int] = None, offset: int = 0) -> list[dict[str, Any]]: ...
    def count(self, table: str, where: Optional[dict[str, Any]] = None) -> int: ...


class SQLiteRepository:
    backend = "sqlite"

    def __init__(self, path: str = ":memory:"):
        if path != ":memory:":
            Path(path).parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._lock = threading.RLock()
        with self._lock:
            self._conn.executescript(SQLITE_SCHEMA)
            cols = {r[1] for r in self._conn.execute("PRAGMA table_info(users)")}
            if "password_hash" not in cols:  # upgrade a database created before auth existed
                self._conn.execute("ALTER TABLE users ADD COLUMN password_hash TEXT")
            self._conn.commit()

    # --- (de)serialisation of JSON / bool columns ---
    @staticmethod
    def _encode(table: str, row: dict[str, Any]) -> dict[str, Any]:
        out = dict(row)
        for c in JSON_COLUMNS.get(table, ()):
            if c in out and not isinstance(out[c], str) and out[c] is not None:
                out[c] = json.dumps(out[c])
        for c in BOOL_COLUMNS.get(table, ()):
            if c in out and out[c] is not None:
                out[c] = int(bool(out[c]))
        return out

    @staticmethod
    def _decode(table: str, row: sqlite3.Row | None) -> Optional[dict[str, Any]]:
        if row is None:
            return None
        out = dict(row)
        for c in JSON_COLUMNS.get(table, ()):
            if isinstance(out.get(c), str):
                try:
                    out[c] = json.loads(out[c])
                except json.JSONDecodeError:
                    pass
        for c in BOOL_COLUMNS.get(table, ()):
            if out.get(c) is not None:
                out[c] = bool(out[c])
        return out

    def insert(self, table, row):
        row = self._encode(table, row)
        cols = ", ".join(row)
        marks = ", ".join("?" for _ in row)
        with self._lock:
            self._conn.execute(f"INSERT INTO {table} ({cols}) VALUES ({marks})", list(row.values()))
            self._conn.commit()
        return self.get(table, row[PRIMARY_KEYS[table]])

    def get(self, table, key):
        with self._lock:
            cur = self._conn.execute(f"SELECT * FROM {table} WHERE {PRIMARY_KEYS[table]} = ?", (key,))
            return self._decode(table, cur.fetchone())

    def update(self, table, key, patch):
        patch = self._encode(table, patch)
        if not patch:
            return self.get(table, key)
        sets = ", ".join(f"{c} = ?" for c in patch)
        with self._lock:
            self._conn.execute(f"UPDATE {table} SET {sets} WHERE {PRIMARY_KEYS[table]} = ?", [*patch.values(), key])
            self._conn.commit()
        return self.get(table, key)

    def _where(self, where):
        if not where:
            return "", []
        return " WHERE " + " AND ".join(f"{c} = ?" for c in where), list(where.values())

    def list(self, table, where=None, order_by=None, desc=True, limit=None, offset=0):
        clause, params = self._where(where)
        sql = f"SELECT * FROM {table}{clause}"
        if order_by:
            sql += f" ORDER BY {order_by} {'DESC' if desc else 'ASC'}"
        if limit is not None:
            sql += f" LIMIT {int(limit)} OFFSET {int(offset)}"
        with self._lock:
            return [self._decode(table, r) for r in self._conn.execute(sql, params).fetchall()]

    def count(self, table, where=None):
        clause, params = self._where(where)
        with self._lock:
            return int(self._conn.execute(f"SELECT COUNT(*) FROM {table}{clause}", params).fetchone()[0])


class SupabaseRepository:
    """Supabase (PostgREST) backend. Use the service-role key on the server only."""
    backend = "supabase"

    def __init__(self, url: str, key: str):
        from supabase import create_client  # imported lazily so SQLite mode needs no SDK

        self._sb = create_client(url, key)

    def insert(self, table, row):
        return self._sb.table(table).insert(row).execute().data[0]

    def get(self, table, key):
        data = self._sb.table(table).select("*").eq(PRIMARY_KEYS[table], key).limit(1).execute().data
        return data[0] if data else None

    def update(self, table, key, patch):
        data = self._sb.table(table).update(patch).eq(PRIMARY_KEYS[table], key).execute().data
        return data[0] if data else None

    def list(self, table, where=None, order_by=None, desc=True, limit=None, offset=0):
        q = self._sb.table(table).select("*")
        for c, v in (where or {}).items():
            q = q.eq(c, v)
        if order_by:
            q = q.order(order_by, desc=desc)
        if limit is not None:
            q = q.range(offset, offset + int(limit) - 1)
        return q.execute().data

    def count(self, table, where=None):
        q = self._sb.table(table).select("*", count="exact", head=True)
        for c, v in (where or {}).items():
            q = q.eq(c, v)
        return int(q.execute().count or 0)


_repo: Optional[Repository] = None


def get_repo() -> Repository:
    global _repo
    if _repo is None:
        from ..config import settings

        if settings.supabase_url and settings.supabase_key:
            _repo = SupabaseRepository(settings.supabase_url, settings.supabase_key)
        else:
            _repo = SQLiteRepository(settings.sqlite_path)
    return _repo


def set_repo(repo: Optional[Repository]) -> None:
    """Swap the repository (used by tests)."""
    global _repo
    _repo = repo
