import json
from .base import chat_json
from ..schemas import RemediationOutput

SYSTEM = """You are a DevOps remediation expert. For each issue provided, give a concrete, specific fix.
Return ONLY valid JSON:
{
  "remediations": [
    {
      "issue_summary": "copy the issue summary here",
      "root_cause": "specific root cause based on the evidence",
      "fix": "exact commands or step-by-step instructions to fix",
      "rationale": "why this fix resolves the root cause"
    }
  ]
}
Provide one remediation per issue. Be specific — no generic advice."""


def run_remediation(issues: list[dict]) -> list[dict]:
    if not issues:
        return []
    output = chat_json(SYSTEM, json.dumps(issues), RemediationOutput)
    return [r.model_dump() for r in output.remediations]
