import os
import time
import markdown as md_lib
from functools import wraps
from flask import (
    Flask,
    render_template,
    request,
    redirect,
    url_for,
    session,
    flash,
    jsonify,
)
from authlib.integrations.flask_client import OAuth
from .config import (
    SECRET_KEY,
    PAYMENT_LINK,
    PRO_PRICE,
    ADMIN_EMAILS,
    LOOM_VIDEO_URL,
    GOOGLE_CLIENT_ID,
    GOOGLE_CLIENT_SECRET,
    DEEPSEEK_MODEL,
)
from .db import db_enabled, init_db, migrate_json_users, record_event
from .auth import (
    register_user,
    login_user,
    login_user_oauth,
    get_user,
    upgrade_to_pro,
    increment_logs_analyzed,
    get_all_users,
    seed_admin_users,
)
from .graph import run_pipeline

app = Flask(__name__)
app.secret_key = SECRET_KEY

oauth = OAuth(app)
if GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET:
    oauth.register(
        name="google",
        client_id=GOOGLE_CLIENT_ID,
        client_secret=GOOGLE_CLIENT_SECRET,
        server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
        client_kwargs={"scope": "openid email profile"},
    )


@app.context_processor
def inject_google_enabled():
    return {"google_enabled": bool(GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET)}


def client_ip():
    ip = request.headers.get("X-Forwarded-For", request.remote_addr)
    return ip.split(",")[0].strip() if ip else None


def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if "user_email" not in session:
            flash("Sign in to access this page.", "info")
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated


def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if "user_email" not in session:
            return redirect(url_for("login"))
        user = get_user(session["user_email"])
        if not user or not user.get("is_admin"):
            flash("Admin access required.", "error")
            return redirect(url_for("dashboard"))
        return f(*args, **kwargs)
    return decorated


@app.route("/")
def landing():
    user = None
    if "user_email" in session:
        user = get_user(session["user_email"])
    return render_template("landing.html", user=user, price=PRO_PRICE, loom_url=LOOM_VIDEO_URL)


@app.route("/signup", methods=["GET", "POST"])
def signup():
    if "user_email" in session:
        return redirect(url_for("dashboard"))

    prefill = {}

    if request.method == "POST":
        first_name = request.form.get("first_name", "").strip()
        last_name = request.form.get("last_name", "").strip()
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "")
        confirm = request.form.get("confirm_password", "")

        if not all([first_name, last_name, email, password]):
            flash("All fields are required.", "error")
            return render_template("signup.html", prefill=prefill)

        if password != confirm:
            flash("Passwords do not match.", "error")
            return render_template("signup.html", prefill=prefill)

        if len(password) < 6:
            flash("Password must be at least 6 characters.", "error")
            return render_template("signup.html", prefill=prefill)

        result = register_user(
            first_name, last_name, email, password,
            signup_ip=client_ip(),
            user_agent=request.user_agent.string,
        )
        if not result["ok"]:
            record_event("signup", user_email=email, status="failed",
                         details={"error": result["error"]}, request=request)
            flash(result["error"], "error")
            return render_template("signup.html", prefill=prefill)

        record_event("signup", user_email=email, user_id=result["user"]["id"],
                     details={"provider": "email"}, request=request)
        session["user_email"] = email
        flash(f"Welcome to DevOps-Rx, {first_name}!", "success")
        return redirect(url_for("dashboard"), 303)

    return render_template("signup.html", prefill=prefill)


@app.route("/login", methods=["GET", "POST"])
def login():
    if "user_email" in session:
        return redirect(url_for("dashboard"))

    if request.method == "POST":
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "")

        if not email or not password:
            flash("Email and password are required.", "error")
            return render_template("login.html")

        result = login_user(email, password)
        if not result["ok"]:
            record_event("login_failed", user_email=email, status="failed",
                         details={"error": result["error"]}, request=request)
            flash(result["error"], "error")
            return render_template("login.html")

        session["user_email"] = email
        user = result["user"]
        record_event("login", user_email=email, user_id=user["id"],
                     details={"provider": "email", "login_count": user["login_count"]},
                     request=request)
        flash(f"Welcome back, {user['first_name']}!", "success")
        return redirect(url_for("dashboard"), 303)

    return render_template("login.html")


@app.route("/logout")
def logout():
    email = session.get("user_email")
    if email:
        record_event("logout", user_email=email, request=request)
    session.clear()
    flash("You've been signed out.", "info")
    return redirect(url_for("landing"))


@app.route("/dashboard")
@login_required
def dashboard():
    user = get_user(session["user_email"])
    if not user:
        session.clear()
        return redirect(url_for("login"))
    return render_template("dashboard.html", user=user, price=PRO_PRICE)


@app.route("/analyze", methods=["GET", "POST"])
@login_required
def analyze():
    user = get_user(session["user_email"])
    if not user:
        session.clear()
        return redirect(url_for("login"))

    result = None
    log_text = ""

    if request.method == "POST":
        log_text = request.form.get("log_text", "").strip()

        uploaded = request.files.get("log_file")
        if uploaded and uploaded.filename:
            try:
                log_text = uploaded.read().decode("utf-8", errors="replace")
            except Exception:
                flash("Could not read the uploaded file.", "error")
                return render_template("analyze.html", user=user, result=None, log_text="")

        if not log_text:
            flash("Paste log text or upload a log file.", "error")
            return render_template("analyze.html", user=user, result=None, log_text="")

        if len(log_text) > 8000:
            flash(
                "Your log is large — only the first ~8,000 characters will be analyzed. "
                "For full coverage, pre-filter to error/warning lines before uploading.",
                "warning",
            )

        is_pro = user["plan"] == "pro"
        log_source = "upload" if (uploaded and uploaded.filename) else "paste"
        started = time.monotonic()

        try:
            if is_pro:
                result = run_pipeline(log_text)
                result["plan_truncated"] = False
                result["total_issues"] = len(result.get("issues", []))
            else:
                from .agents.classifier import run_classifier
                issues, log_truncated = run_classifier(log_text)
                total = len(issues)
                result = {
                    "issues": issues[:2],
                    "remediations": [],
                    "checklist": "",
                    "jira_keys": [],
                    "slack_status": "skipped",
                    "log_truncated": log_truncated,
                    "plan_truncated": total > 2,
                    "total_issues": total,
                    "error": None,
                }
        except Exception as exc:
            import traceback
            print(f"[devops-rx] analyze error: {traceback.format_exc()}", flush=True)
            flash(f"Analysis failed: {str(exc)[:200]}", "error")
            return render_template("analyze.html", user=user, result=None,
                                   log_text=log_text, price=PRO_PRICE)

        increment_logs_analyzed(session["user_email"])
        record_event(
            "analyze_log",
            user_email=session["user_email"],
            user_id=user["id"],
            status="failed" if result.get("error") else "success",
            details={
                "log_chars": len(log_text),
                "log_source": log_source,
                "issues_found": result.get("total_issues", 0),
                "issues_shown": len(result.get("issues", [])),
                "severities": [i.get("severity") for i in result.get("issues", [])],
                "duration_ms": int((time.monotonic() - started) * 1000),
                "model": DEEPSEEK_MODEL,
                "plan": user["plan"],
                "jira_keys": result.get("jira_keys", []),
                "error": result.get("error"),
            },
            request=request,
        )

        if result.get("checklist"):
            result["checklist_html"] = md_lib.markdown(
                result["checklist"], extensions=["fenced_code", "tables"]
            )
        else:
            result["checklist_html"] = ""

    return render_template("analyze.html", user=user, result=result, log_text=log_text, price=PRO_PRICE)


@app.route("/pricing")
def pricing():
    user = None
    if "user_email" in session:
        user = get_user(session["user_email"])
    return render_template("pricing.html", user=user, payment_link=PAYMENT_LINK, price=PRO_PRICE)


@app.route("/payment/success")
@login_required
def payment_success():
    user = get_user(session["user_email"])
    if user and user["plan"] != "pro":
        upgrade_to_pro(session["user_email"])
        record_event("upgrade_pro", user_email=session["user_email"], user_id=user["id"],
                     details={"price": PRO_PRICE, "route": "stripe"}, request=request)
        flash("Your account has been upgraded to Pro!", "success")
    return redirect(url_for("dashboard"))


@app.route("/payment/simulate")
@login_required
def payment_simulate():
    upgrade_to_pro(session["user_email"])
    record_event("payment_simulate", user_email=session["user_email"],
                 details={"price": PRO_PRICE, "route": "demo"}, request=request)
    flash("Demo upgrade complete. You now have Pro access.", "success")
    return redirect(url_for("dashboard"))


@app.route("/admin/users")
@admin_required
def admin_users():
    users = get_all_users()
    return render_template("admin_users.html", users=users)


@app.route("/auth/google")
def google_auth():
    if not GOOGLE_CLIENT_ID or not GOOGLE_CLIENT_SECRET:
        flash("Google sign-in is not configured yet. Please use email sign-up.", "info")
        return redirect(url_for("signup"))
    redirect_uri = url_for("google_callback", _external=True)
    return oauth.google.authorize_redirect(redirect_uri)


@app.route("/auth/google/callback")
def google_callback():
    if not GOOGLE_CLIENT_ID or not GOOGLE_CLIENT_SECRET:
        flash("Google sign-in is not configured.", "error")
        return redirect(url_for("login"))
    try:
        token = oauth.google.authorize_access_token()
        userinfo = token.get("userinfo") or oauth.google.userinfo()
        email = userinfo.get("email", "").strip().lower()
        first_name = userinfo.get("given_name", "").strip() or userinfo.get("name", "User").split()[0]
        last_name = userinfo.get("family_name", "").strip() or ""
        if not email:
            flash("Could not retrieve your Google email. Please try email sign-up.", "error")
            return redirect(url_for("signup"))
        result = login_user_oauth(
            email, first_name, last_name, provider="google",
            signup_ip=client_ip(),
            user_agent=request.user_agent.string,
        )
        record_event("google_login", user_email=email, user_id=result["user"]["id"],
                     details={"provider": "google"}, request=request)
        session["user_email"] = email
        flash(f"Welcome, {result['user']['first_name']}!", "success")
        return redirect(url_for("dashboard"), 303)
    except Exception as exc:
        flash(f"Google sign-in failed: {exc}", "error")
        return redirect(url_for("login"))


try:
    if db_enabled():
        init_db()
        migrated = migrate_json_users()
        if migrated:
            print(f"[devops-rx] migrated {migrated} user(s) from users.json to PostgreSQL", flush=True)
except Exception as _startup_exc:
    print(f"[devops-rx] WARNING: DB startup error ({_startup_exc}), continuing with JSON.", flush=True)
seed_admin_users()
