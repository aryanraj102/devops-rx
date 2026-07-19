import json
from .base import chat


SYSTEM = """You are a senior SRE writing an incident runbook. Convert the remediations into a numbered markdown checklist.
- Group related fixes under bold headers
- List prerequisites at the top
- Use code blocks for commands
- Be specific and actionable
- Add a verification step after each fix"""


def run_cookbook(remediations: list[dict]) -> str:
    if not remediations:
        return "No issues found — nothing to remediate."
    return chat(SYSTEM, json.dumps(remediations))
