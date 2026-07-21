import json
import os
import uuid
from datetime import datetime
from typing import Optional
from werkzeug.security import generate_password_hash, check_password_hash
from .config import USERS_FILE, ADMIN_EMAILS, APP_NAME
from .db import db_enabled, get_conn, row_to_user, USER_COLUMNS


def _load_users() -> dict:
    if not os.path.exists(USERS_FILE):
        os.makedirs(os.path.dirname(USERS_FILE), exist_ok=True)
        return {}
    with open(USERS_FILE) as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return {}


def _save_users(users: dict):
    os.makedirs(os.path.dirname(USERS_FILE), exist_ok=True)
    with open(USERS_FILE, "w") as f:
        json.dump(users, f, indent=2)


def _warn(fn: str, exc: Exception):
    print(f"[devops-rx] WARNING: {fn} db error ({exc}), falling back to JSON", flush=True)


def hash_password(password: str) -> str:
    return generate_password_hash(password)


def register_user(first_name: str, last_name: str, email: str, password: str,
                  source_app: str = None, signup_ip: str = None,
                  user_agent: str = None) -> dict:
    email = email.lower().strip()
    is_admin = email in [a.lower() for a in ADMIN_EMAILS]
    record = {
        "id": str(uuid.uuid4()),
        "first_name": first_name.strip(),
        "last_name": last_name.strip(),
        "email": email,
        "password_hash": hash_password(password),
        "plan": "pro" if is_admin else "free",
        "is_admin": is_admin,
        "joined_at": datetime.utcnow().isoformat(),
        "last_login": None,
        "login_count": 0,
        "provider": "email",
        "logs_analyzed": 0,
    }

    if db_enabled():
        try:
            with get_conn() as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        INSERT INTO users (id, email, first_name, last_name, password_hash,
                                           plan, is_admin, provider, source_app,
                                           signup_ip, signup_user_agent, joined_at)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        ON CONFLICT (email) DO NOTHING
                    """, (
                        record["id"], email, record["first_name"], record["last_name"],
                        record["password_hash"], record["plan"], is_admin, "email",
                        source_app or APP_NAME, signup_ip, user_agent, record["joined_at"],
                    ))
                    if cur.rowcount == 0:
                        return {"ok": False, "error": "An account with this email already exists."}
            return {"ok": True, "user": record}
        except Exception as exc:
            _warn("register_user", exc)

    users = _load_users()
    if email in users:
        return {"ok": False, "error": "An account with this email already exists."}
    users[email] = record
    _save_users(users)
    return {"ok": True, "user": record}


def login_user(email: str, password: str) -> dict:
    email = email.lower().strip()

    if db_enabled():
        try:
            with get_conn() as conn:
                with conn.cursor() as cur:
                    cur.execute(f"SELECT {USER_COLUMNS} FROM users WHERE email = %s", (email,))
                    row = cur.fetchone()
                    if not row:
                        return {"ok": False, "error": "No account found with this email."}
                    user = row_to_user(row)
                    if not check_password_hash(user.get("password_hash", ""), password):
                        return {"ok": False, "error": "Incorrect password."}
                    cur.execute("""
                        UPDATE users
                        SET last_login = now(), login_count = login_count + 1, updated_at = now()
                        WHERE email = %s RETURNING last_login, login_count
                    """, (email,))
                    last_login, login_count = cur.fetchone()
                    user["last_login"] = last_login.isoformat()
                    user["login_count"] = login_count
            return {"ok": True, "user": user}
        except Exception as exc:
            _warn("login_user", exc)

    users = _load_users()
    user = users.get(email)
    if not user:
        return {"ok": False, "error": "No account found with this email."}
    if not check_password_hash(user.get("password_hash", ""), password):
        return {"ok": False, "error": "Incorrect password."}
    user["last_login"] = datetime.utcnow().isoformat()
    user["login_count"] = user.get("login_count", 0) + 1
    _save_users(users)
    return {"ok": True, "user": user}


def get_user(email: str) -> Optional[dict]:
    email = email.lower().strip()
    if db_enabled():
        import time
        for attempt in range(2):
            try:
                with get_conn() as conn:
                    with conn.cursor() as cur:
                        cur.execute(f"SELECT {USER_COLUMNS} FROM users WHERE email = %s", (email,))
                        row = cur.fetchone()
                return row_to_user(row) if row else None
            except Exception as exc:
                _warn("get_user", exc)
                if attempt == 0:
                    time.sleep(0.3)  # brief pause before retrying transient DB error

    return _load_users().get(email)


def upgrade_to_pro(email: str):
    email = email.lower().strip()
    if db_enabled():
        try:
            with get_conn() as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        UPDATE users SET plan = 'pro', upgraded_at = now(), updated_at = now()
                        WHERE email = %s
                    """, (email,))
            return
        except Exception as exc:
            _warn("upgrade_to_pro", exc)

    users = _load_users()
    if email in users:
        users[email]["plan"] = "pro"
        users[email]["upgraded_at"] = datetime.utcnow().isoformat()
        _save_users(users)


def increment_logs_analyzed(email: str):
    email = email.lower().strip()
    if db_enabled():
        try:
            with get_conn() as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        UPDATE users SET logs_analyzed = logs_analyzed + 1, updated_at = now()
                        WHERE email = %s
                    """, (email,))
            return
        except Exception as exc:
            _warn("increment_logs_analyzed", exc)

    users = _load_users()
    if email in users:
        users[email]["logs_analyzed"] = users[email].get("logs_analyzed", 0) + 1
        _save_users(users)


def get_all_users() -> list:
    if db_enabled():
        try:
            with get_conn() as conn:
                with conn.cursor() as cur:
                    cur.execute(f"SELECT {USER_COLUMNS} FROM users ORDER BY joined_at")
                    rows = cur.fetchall()
            safe = []
            for row in rows:
                user = row_to_user(row)
                user.pop("password_hash", None)
                safe.append(user)
            return safe
        except Exception as exc:
            _warn("get_all_users", exc)

    users = _load_users()
    return [{k: v for k, v in u.items() if k != "password_hash"} for u in users.values()]


def login_user_oauth(email: str, first_name: str, last_name: str,
                     provider: str = "google", source_app: str = None,
                     signup_ip: str = None, user_agent: str = None) -> dict:
    email = email.lower().strip()
    is_admin = email in [a.lower() for a in ADMIN_EMAILS]

    if db_enabled():
        try:
            with get_conn() as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        INSERT INTO users (id, email, first_name, last_name, password_hash,
                                           plan, is_admin, provider, source_app,
                                           signup_ip, signup_user_agent)
                        VALUES (%s, %s, %s, %s, '', %s, %s, %s, %s, %s, %s)
                        ON CONFLICT (email) DO NOTHING
                    """, (
                        str(uuid.uuid4()), email, first_name.strip(), last_name.strip(),
                        "pro" if is_admin else "free", is_admin, provider,
                        source_app or APP_NAME, signup_ip, user_agent,
                    ))
                    cur.execute("""
                        UPDATE users
                        SET last_login = now(), login_count = login_count + 1, updated_at = now()
                        WHERE email = %s
                    """, (email,))
                    cur.execute(f"SELECT {USER_COLUMNS} FROM users WHERE email = %s", (email,))
                    user = row_to_user(cur.fetchone())
            return {"ok": True, "user": user}
        except Exception as exc:
            _warn("login_user_oauth", exc)

    users = _load_users()
    if email not in users:
        users[email] = {
            "id": str(uuid.uuid4()),
            "first_name": first_name.strip(), "last_name": last_name.strip(),
            "email": email, "password_hash": "",
            "plan": "pro" if is_admin else "free", "is_admin": is_admin,
            "joined_at": datetime.utcnow().isoformat(), "last_login": None,
            "login_count": 0, "provider": provider, "logs_analyzed": 0,
        }
    user = users[email]
    user["last_login"] = datetime.utcnow().isoformat()
    user["login_count"] = user.get("login_count", 0) + 1
    _save_users(users)
    return {"ok": True, "user": user}


def seed_admin_users():
    import os
    seed_json = os.environ.get("SEED_USERS", "")
    if not seed_json:
        return
    try:
        import json
        admins = json.loads(seed_json)
    except Exception:
        return
    for a in admins:
        if not get_user(a["email"]):
            register_user(a["first_name"], a["last_name"], a["email"], a["password"])
