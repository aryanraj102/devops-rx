from typing import TypedDict
from langgraph.graph import StateGraph, START, END

from .agents.classifier import run_classifier
from .agents.remediation import run_remediation
from .agents.cookbook import run_cookbook
from .agents.jira_agent import run_jira
from .agents.slack_agent import run_slack


class State(TypedDict, total=False):
    raw_log: str
    issues: list
    log_truncated: bool
    remediations: list
    checklist: str
    jira_keys: list
    slack_status: str
    error: str


def classify(s: State) -> dict:
    issues, truncated = run_classifier(s["raw_log"])
    return {"issues": issues, "log_truncated": truncated}


def remediate(s: State) -> dict:
    return {"remediations": run_remediation(s["issues"])}


def cookbook(s: State) -> dict:
    return {"checklist": run_cookbook(s["remediations"])}


def jira(s: State) -> dict:
    return {"jira_keys": run_jira(s["issues"])}


def slack(s: State) -> dict:
    return {"slack_status": run_slack(
        s.get("issues", []),
        s.get("checklist", ""),
        s.get("jira_keys", []),
    )}


def _route(s: State) -> str:
    if any(i.get("severity") == "critical" for i in s.get("issues", [])):
        return "jira"
    return "slack"


g = StateGraph(State)

for name, fn in [
    ("classify", classify),
    ("remediate", remediate),
    ("cookbook", cookbook),
    ("jira", jira),
    ("slack", slack),
]:
    g.add_node(name, fn)

g.add_edge(START, "classify")
g.add_edge("classify", "remediate")
g.add_edge("remediate", "cookbook")
g.add_conditional_edges("cookbook", _route, {"jira": "jira", "slack": "slack"})
g.add_edge("jira", "slack")
g.add_edge("slack", END)

_pipeline = g.compile()


def run_pipeline(raw_log: str) -> dict:
    return _pipeline.invoke({"raw_log": raw_log})
