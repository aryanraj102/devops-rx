import json
import logging
import requests
from requests.auth import HTTPBasicAuth
from .base import chat_json
from ..config import JIRA_URL, JIRA_EMAIL, JIRA_TOKEN, JIRA_PROJECT

logger = logging.getLogger(__name__)

_TICKET_SCHEMA = '{"summary": "...", "description": "..."}'

SYSTEM = f'Draft a Jira ticket. Return JSON: {_TICKET_SCHEMA}'


def run_jira(issues: list[dict]) -> list[str]:
    if not JIRA_URL or not JIRA_TOKEN:
        return []

    critical = [i for i in issues if i["severity"] == "critical"]
    keys = []

    for issue in critical:
        try:
            from ..schemas import JiraTicket
            ticket = chat_json(SYSTEM, json.dumps(issue), JiraTicket)
            r = requests.post(
                f"{JIRA_URL}/rest/api/3/issue",
                auth=HTTPBasicAuth(JIRA_EMAIL, JIRA_TOKEN),
                json={
                    "fields": {
                        "project": {"key": JIRA_PROJECT},
                        "summary": ticket.summary,
                        "description": {
                            "type": "doc",
                            "version": 1,
                            "content": [
                                {
                                    "type": "paragraph",
                                    "content": [{"type": "text", "text": ticket.description}],
                                }
                            ],
                        },
                        "issuetype": {"name": "Bug"},
                    }
                },
                timeout=30,
            )
            if r.status_code in (200, 201):
                keys.append(r.json().get("key", ""))
            else:
                logger.warning("[jira] ticket creation failed: HTTP %s — %s", r.status_code, r.text[:200])
        except Exception as e:
            logger.warning("[jira] ticket creation failed: %s", e)

    return keys
