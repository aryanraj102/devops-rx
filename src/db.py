"""PostgreSQL layer for DevOps-Rx.

Active only when DATABASE_URL is set; otherwise the app keeps using the
JSON file store in auth.py. All SQL lives here.
"""
import json
import os
from contextlib import contextmanager
from datetime import datetime

from .config import DATABASE_URL, APP_NAME, USERS_FILE

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id            UUID PRIMARY KEY,
    email         TEXT UNIQUE NOT NULL,
    first_name    TEXT NOT NULL,
    last_name     TEXT NOT NULL DEFAULT '',
    password_hash TEXT NOT NULL DEFAULT '',
    plan          TEXT NOT NULL DEFAULT 'free' CHECK (plan IN ('free', 'pro')),
    is_admin      BOOLEAN NOT NULL DEFAULT FALSE,
    provider      TEXT NOT NULL DEFAULT 'email',
    source_app    TEXT NOT NULL DEFAULT 'devops-rx',
    signup_ip     TEXT,
    signup_user_agent TEXT,
    joined_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
    last_login    TIMESTAMPTZ,
    login_count   INTEGER NOT NULL DEFAULT 0,
    logs_analyzed INTEGER NOT NULL DEFAULT 0,
    upgraded_at   TIMESTAMPTZ,
    updated_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_users_source_app ON users (source_app);

CREATE TABLE IF NOT EXISTS transaction_history (
    id          BIGSERIAL PRIMARY KEY,
    occurred_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    user_id     UUID REFERENCES users(id) ON DELETE SET NULL,
    user_email  TEXT,
    source_app  TEXT NOT NULL DEFAULT 'devops-rx',
    action      TEXT NOT NULL,
    status      TEXT NOT NULL DEFAULT 'success',
    ip_address  TEXT,
    user_agent  TEXT,
    http_method TEXT,
    path        TEXT,
    details     JSONB NOT NULL DEFAULT '{}'::jsonb
);
CREATE INDEX IF NOT EXISTS idx_txn_user_time ON transaction_history (user_email, occurred_at DESC);
CREATE INDEX IF NOT EXISTS idx_txn_action    ON transaction_history (action);
"""

USER_COLUMNS = (
    "id, email, first_name, last_name, password_hash, plan, is_admin, provider, "
    "source_app, signup_ip, signup_user_agent, joined_at, last_login, login_count, "
    "logs_analyzed, upgraded_at"
)


def db_enabled() -> bool:
    return bool(DATABASE_URL)


@contextmanager
def get_conn():
    import psycopg2

    url = DATABASE_URL
    if "localhost" not in url and "127.0.0.1" not in url and "sslmode" not in url:
        sep = "&" if "?" in url else "?"
        url = f"{url}{sep}sslmode=require"

    conn = psycopg2.connect(url)
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db():
    try:
        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute(SCHEMA)
    except Exception as exc:
        print(f"[devops-rx] WARNING: init_db failed ({exc}). Running without PostgreSQL.", flush=True)


def row_to_user(row) -> dict:
    keys = [c.strip() for c in USER_COLUMNS.split(",")]
    user = dict(zip(keys, row))
    user["id"] = str(user["id"])
    for ts in ("joined_at", "last_login", "upgraded_at"):
        if isinstance(user.get(ts), datetime):
            user[ts] = user[ts].isoformat()
    if user.get("upgraded_at") is None:
        user.pop("upgraded_at")
    return user


def migrate_json_users():
    if not os.path.exists(USERS_FILE):
        return 0
    try:
        with open(USERS_FILE) as f:
            users = json.load(f)
    except (json.JSONDecodeError, OSError):
        return 0
    if not users:
        return 0
    imported = 0
    try:
        with get_conn() as conn:
            with conn.cursor() as cur:
                for u in users.values():
                    cur.execute(
                        """
                        INSERT INTO users (id, email, first_name, last_name, password_hash,
                                           plan, is_admin, provider, source_app, joined_at,
                                           last_login, login_count, logs_analyzed, upgraded_at)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        ON CONFLICT (email) DO NOTHING
                        """,
                        (
                            u["id"],
                            u["email"].lower().strip(),
                            u.get("first_name", ""),
                            u.get("last_name", ""),
                            u.get("password_hash", ""),
                            u.get("plan", "free"),
                            u.get("is_admin", False),
                            u.get("provider", "email"),
                            APP_NAME,
                            u.get("joined_at"),
                            u.get("last_login"),
                            u.get("login_count", 0),
                            u.get("logs_analyzed", 0),
                            u.get("upgraded_at"),
                        ),
                    )
                    imported += cur.rowcount
    except Exception as exc:
        print(f"[devops-rx] WARNING: migrate_json_users failed ({exc}).", flush=True)
    return imported


def record_event(action, user_email=None, user_id=None, status="success",
                 details=None, request=None):
    if not db_enabled():
        return
    ip = user_agent = method = path = None
    if request is not None:
        ip = request.headers.get("X-Forwarded-For", request.remote_addr)
        if ip:
            ip = ip.split(",")[0].strip()
        user_agent = request.user_agent.string if request.user_agent else None
        method = request.method
        path = request.path
    try:
        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO transaction_history
                        (user_id, user_email, source_app, action, status,
                         ip_address, user_agent, http_method, path, details)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s::jsonb)
                    """,
                    (
                        user_id,
                        user_email.lower().strip() if user_email else None,
                        APP_NAME,
                        action,
                        status,
                        ip,
                        user_agent,
                        method,
                        path,
                        json.dumps(details or {}),
                    ),
                )
    except Exception as exc:
        print(f"[devops-rx] WARNING: failed to record '{action}' event: {exc}", flush=True)
