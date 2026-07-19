import json
import logging
import requests
from .base import chat
from ..config import SLACK_WEBHOOK_URL

logger = logging.getLogger(__name__)

SYSTEM = "Format a concise incident summary for Slack. Use sections with emoji. Keep under 500 words."


def run_slack(issues: list[dict], checklist: str, jira_keys: list[str]) -> str:
    if not SLACK_WEBHOOK_URL:
        return "skipped"

    try:
        summary = chat(
            SYSTEM,
            f"Issues: {json.dumps(issues)}\n\nChecklist:\n{checklist}\n\nJira tickets: {jira_keys}",
        )
        r = requests.post(SLACK_WEBHOOK_URL, json={"text": summary}, timeout=15)
        if r.status_code == 200:
            return "ok"
        logger.warning("[slack] post failed: HTTP %s", r.status_code)
        return f"failed (HTTP {r.status_code})"
    except Exception as e:
        logger.warning("[slack] post failed: %s", e)
        return f"failed ({e})"
