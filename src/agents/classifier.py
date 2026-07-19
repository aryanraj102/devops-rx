from .base import chat_json
from ..schemas import ClassifierOutput

LOG_CHAR_LIMIT = 8000

SYSTEM = """You are a log analysis expert. Extract every distinct operational issue from the provided log.
Return ONLY valid JSON in this exact format:
{
  "issues": [
    {
      "service": "name of service/component",
      "severity": "critical|high|medium|low",
      "category": "oom|disk_full|timeout|auth_failure|connection_error|crash|other",
      "summary": "one line describing the issue",
      "evidence": ["exact log line 1", "exact log line 2"]
    }
  ]
}
Do not invent issues. Only report what is clearly in the log. If no issues found, return {"issues": []}."""


def run_classifier(raw_log: str) -> tuple[list[dict], bool]:
    truncated = len(raw_log) > LOG_CHAR_LIMIT
    output = chat_json(SYSTEM, raw_log[:LOG_CHAR_LIMIT], ClassifierOutput)
    return [i.model_dump() for i in output.issues], truncated
