from typing import Literal, Optional
from pydantic import BaseModel


class Issue(BaseModel):
    service: str
    severity: Literal["critical", "high", "medium", "low"]
    category: str
    summary: str
    evidence: list[str]


class ClassifierOutput(BaseModel):
    issues: list[Issue]


class Remediation(BaseModel):
    issue_summary: str
    root_cause: str
    fix: str
    rationale: str


class RemediationOutput(BaseModel):
    remediations: list[Remediation]


class JiraTicket(BaseModel):
    summary: str
    description: str


class PipelineState(BaseModel):
    raw_log: str = ""
    issues: list[dict] = []
    remediations: list[dict] = []
    checklist: str = ""
    jira_keys: list[str] = []
    slack_status: str = "skipped"
    error: Optional[str] = None
