# DevOps-Rx — AI-Powered DevOps Incident Analyzer

![Python](https://img.shields.io/badge/Python-3.11+-blue?style=flat-square&logo=python)
![Flask](https://img.shields.io/badge/Flask-3.0-black?style=flat-square&logo=flask)
![OpenRouter](https://img.shields.io/badge/LLM-DeepSeek%20V3-purple?style=flat-square)
![License](https://img.shields.io/badge/License-MIT-green?style=flat-square)
![Live](https://img.shields.io/badge/Live-devops--rx.onrender.com-brightgreen?style=flat-square)

Upload ops logs. Get a diagnosis, a fix list, and a Jira ticket in under 60 seconds.

**Live demo:** https://devops-rx.onrender.com

---

## What it does

DevOps-Rx takes a raw log file — Linux syslog, Apache access log, Kubernetes events, Nginx — and runs it through three sequential AI agents:

1. **Classifier** — extracts distinct issues with severity, category, and exact log-line evidence
2. **Remediation** — maps each issue to a root cause and a concrete fix
3. **Cookbook** — formats everything into a numbered runbook ready for on-call

Critical issues are automatically filed as Jira tickets and summarized in Slack (Pro plan, credentials required).

---

## Architecture

```
Browser (Flask UI)
        │
        ▼
   run_pipeline()          src/graph.py
        │
   ┌────┼────────────────────────────────┐
   │    ▼                                │
   │  Classifier agent                   │
   │  (DeepSeek V3 via OpenRouter)       │
   │    │ issues[]                        │
   │    ▼                                │
   │  Remediation agent                  │
   │    │ remediations[]                  │
   │    ▼                                │
   │  Cookbook agent                     │
   │    │ checklist (markdown)            │
   │    ▼                                │
   │  [critical issues?]                 │
   │    ├─yes─► Jira agent               │
   │    └─no──► Slack agent              │
   └────────────────────────────────────┘
```

---

## Project Structure

```
devops-rx/
├── src/                    # Application source
│   ├── app.py              # Flask routes
│   ├── auth.py             # Authentication (email + Google OAuth)
│   ├── config.py           # All config from environment variables
│   ├── db.py               # PostgreSQL layer (JSON fallback)
│   ├── graph.py            # LangGraph pipeline
│   ├── schemas.py          # Pydantic models
│   ├── agents/             # AI agents
│   │   ├── classifier.py
│   │   ├── remediation.py
│   │   ├── cookbook.py
│   │   ├── jira_agent.py
│   │   └── slack_agent.py
│   ├── templates/          # Jinja2 HTML templates
│   └── static/             # CSS, JS, assets
├── tests/
│   └── test_app.py
├── docs/
│   ├── runbook.md
│   └── severity_policy.md
├── sample_logs/            # Sample log files for testing
├── wsgi.py                 # Gunicorn entry point
├── requirements.txt
├── render.yaml
└── .env.example
```

---

## Quick Start

```bash
git clone https://github.com/aryanraj102/devops-rx.git
cd devops-rx

python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env
# Edit .env — add your OPENROUTER_API_KEY at minimum

gunicorn wsgi:app --bind 127.0.0.1:5001
# Open http://localhost:5001
```

---

## Test Accounts

Test account credentials are kept in a local file (`TEST_ACCOUNTS.md`) that is not committed to this repository. Seed users are configured via the `SEED_USERS` environment variable — see `.env.example` for the format.

---

## Features

| Feature | Free | Pro |
|---------|------|-----|
| Log classification | 2 issues | Unlimited |
| Remediation steps | 2 | Unlimited |
| Runbook checklist | Partial | Full |
| Jira ticket creation | — | Yes |
| Slack notifications | — | Yes |
| Price | $0 | $49 one-time |

---

## Sample Log Files

| File | What it contains |
|------|-----------------|
| `sample_logs/linux_system.log` | OOM kill, disk full, SSH brute force, nginx crash |
| `sample_logs/apache_access.log` | 500 errors, admin scanner, slow requests |
| `sample_logs/kubernetes.log` | OOMKilled pods, ImagePullBackOff, liveness failures |

---

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `OPENROUTER_API_KEY` | Yes | OpenRouter API key |
| `SECRET_KEY` | Yes | Flask session secret |
| `DATABASE_URL` | Optional | PostgreSQL connection string (falls back to JSON) |
| `DEEPSEEK_MODEL` | Optional | OpenRouter model ID (default: `deepseek/deepseek-chat`) |
| `SLACK_WEBHOOK_URL` | Optional | Incoming webhook URL for Slack notifications |
| `JIRA_URL` | Optional | Atlassian site URL (e.g. `https://yoursite.atlassian.net`) |
| `JIRA_EMAIL` | Optional | Jira account email |
| `JIRA_TOKEN` | Optional | Jira API token |
| `JIRA_PROJECT` | Optional | Jira project key (default: `OPS`) |
| `GOOGLE_CLIENT_ID` | Optional | Google OAuth client ID |
| `GOOGLE_CLIENT_SECRET` | Optional | Google OAuth client secret |

---

## Deployment (Render)

This repo includes a `render.yaml` blueprint. Connect it in the Render dashboard and set the required environment variables:

1. Fork / clone this repo to your GitHub account
2. Go to [Render](https://render.com) → New → Web Service → connect repo
3. Render auto-detects `render.yaml` — build and start commands are pre-configured
4. Set `OPENROUTER_API_KEY`, `DATABASE_URL`, and `SECRET_KEY` in the Environment tab
5. Deploy

Start command used: `gunicorn wsgi:app --bind 0.0.0.0:$PORT --workers 1 --timeout 120`

---

## Running Tests

```bash
python tests/test_app.py
```

---

## License

MIT — see [LICENSE](LICENSE)
