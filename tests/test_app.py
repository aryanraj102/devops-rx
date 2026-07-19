"""
Automated tests for OpsSight. Run with:
    python -m pytest tests/test_app.py -v
    # or directly:
    python tests/test_app.py
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from src.app import app
from src.auth import seed_admin_users, get_all_users, get_user, login_user


def run():
    app.config['TESTING'] = True
    seed_admin_users()
    errors = []

    passed = 0

    def check(label, condition, detail=""):
        nonlocal passed
        if condition:
            passed += 1
            print(f"  PASS  {label}")
        else:
            print(f"  FAIL  {label}: {detail}")
            errors.append(label)

    print("\n=== Auth Tests ===")
    users = get_all_users()
    check("at least 3 seed users exist", len(users) >= 3, str(len(users)))
    admin = get_user("admin@devopsuite.com")
    check("admin is pro", admin and admin["plan"] == "pro")
    check("admin is_admin flag", admin and admin["is_admin"] is True)
    free = get_user("testuser@devopsuite.com")
    check("testuser is free", free and free["plan"] == "free")
    check("testuser not admin", free and free["is_admin"] is False)
    r = login_user("admin@devopsuite.com", "Admin@2024!")
    check("admin login OK", r["ok"])
    r = login_user("admin@devopsuite.com", "wrongpass")
    check("wrong password rejected", not r["ok"])
    r = login_user("nobody@nobody.com", "pw")
    check("unknown email rejected", not r["ok"])

    print("\n=== Route Tests ===")
    client = app.test_client()
    r = client.get("/")
    check("GET / returns 200", r.status_code == 200)
    check("Landing has hero text", b"Log analysis" in r.data)
    check("Landing has OpsSight brand", b"OpsSight" in r.data)

    r = client.get("/pricing")
    check("GET /pricing returns 200", r.status_code == 200)
    check("Pricing has 'one-time'", b"one-time" in r.data)
    check("Pricing has '$50'", b"50" in r.data)

    r = client.get("/login")
    check("GET /login returns 200", r.status_code == 200)
    check("Login has form", b"Sign in" in r.data)

    r = client.get("/signup")
    check("GET /signup returns 200", r.status_code == 200)
    check("Signup has form", b"Create your account" in r.data)

    r = client.get("/dashboard")
    check("Dashboard unauthenticated redirects", r.status_code == 302)

    r = client.get("/analyze")
    check("Analyze unauthenticated redirects", r.status_code == 302)

    r = client.get("/admin/users")
    check("Admin unauthenticated redirects", r.status_code == 302)

    print("\n=== Auth Flow Tests ===")
    c1 = app.test_client()
    r = c1.post("/login", data={"email": "admin@devopsuite.com", "password": "Admin@2024!"}, follow_redirects=True)
    check("Admin login redirects to dashboard", r.status_code == 200)
    check("Dashboard shows Welcome", b"Welcome back" in r.data or b"Welcome" in r.data)
    r = c1.get("/admin/users")
    check("Admin can access /admin/users", r.status_code == 200)
    check("Admin page lists users", b"admin@devopsuite.com" in r.data)

    c2 = app.test_client()
    r = c2.post("/login", data={"email": "testuser@devopsuite.com", "password": "Test@2024"}, follow_redirects=True)
    check("Free user login OK", r.status_code == 200)
    r = c2.get("/admin/users", follow_redirects=True)
    check("Free user blocked from admin", b"Admin access" in r.data)

    import time, random
    fresh_email = f"testfresh{random.randint(10000,99999)}@test.com"
    c3 = app.test_client()
    r = c3.post("/signup", data={
        "first_name": "Fresh", "last_name": "User",
        "email": fresh_email, "password": "Test@123",
        "confirm_password": "Test@123"
    }, follow_redirects=True)
    check("New user signup OK", r.status_code == 200)
    check("New user sees dashboard", b"Welcome to OpsSight" in r.data or b"Dashboard" in r.data or b"Welcome" in r.data)

    c4 = app.test_client()
    r = c4.post("/signup", data={
        "first_name": "Fresh", "last_name": "User",
        "email": fresh_email, "password": "Test@123",
        "confirm_password": "Test@123"
    }, follow_redirects=True)
    check("Duplicate signup blocked", b"already exists" in r.data)

    c5 = app.test_client()
    r = c5.post("/login", data={"email": "admin@devopsuite.com", "password": "Admin@2024!"}, follow_redirects=True)
    r = c5.get("/payment/simulate", follow_redirects=True)
    check("Payment simulate works", r.status_code == 200)

    print("\n=== Graph / Agent Import Tests ===")
    try:
        from src.graph import run_pipeline
        check("graph.py imports OK", True)
    except Exception as e:
        check("graph.py imports OK", False, str(e))

    try:
        from src.agents.classifier import run_classifier
        from src.agents.remediation import run_remediation
        from src.agents.cookbook import run_cookbook
        check("All agent imports OK", True)
    except Exception as e:
        check("All agent imports OK", False, str(e))

    print(f"\n{'='*40}")
    if errors:
        print(f"FAILED: {len(errors)} test(s): {errors}")
        return 1
    else:
        print(f"ALL {passed} TESTS PASSED")
        return 0


if __name__ == "__main__":
    sys.exit(run())
