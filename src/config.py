import os
import sys
from dotenv import load_dotenv

load_dotenv()

def _require(var: str) -> str:
    val = os.environ.get(var)
    if not val:
        print(f"[devops-rx] FATAL: environment variable '{var}' is not set. "
              f"Add it in your Render dashboard → Environment tab.", flush=True)
        sys.exit(1)
    return val

OPENROUTER_API_KEY = _require("OPENROUTER_API_KEY")
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
DEEPSEEK_MODEL = os.environ.get("DEEPSEEK_MODEL", "deepseek/deepseek-chat")

SECRET_KEY = _require("SECRET_KEY")
# data/ lives one level above src/
USERS_FILE = os.path.join(os.path.dirname(__file__), "..", "data", "users.json")

DATABASE_URL = os.environ.get("DATABASE_URL", "")
APP_NAME = os.environ.get("APP_NAME", "devops-rx")

ADMIN_EMAILS = ["admin@devopsuite.com", "rajesh@devopsuite.com"]

PAYMENT_LINK = "https://buy.stripe.com/test_28o3cXeMR0PF0M06oo"
PRO_PRICE = 49

LOOM_VIDEO_URL = os.environ.get("LOOM_VIDEO_URL", "")

GOOGLE_CLIENT_ID = os.environ.get("GOOGLE_CLIENT_ID", "")
GOOGLE_CLIENT_SECRET = os.environ.get("GOOGLE_CLIENT_SECRET", "")

SLACK_WEBHOOK_URL = os.environ.get("SLACK_WEBHOOK_URL", "")
JIRA_URL = os.environ.get("JIRA_URL", "")
JIRA_EMAIL = os.environ.get("JIRA_EMAIL", "")
JIRA_TOKEN = os.environ.get("JIRA_TOKEN", "")
JIRA_PROJECT = os.environ.get("JIRA_PROJECT", "OPS")
