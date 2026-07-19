import json
import requests
from pydantic import ValidationError
from ..config import OPENROUTER_API_KEY, OPENROUTER_BASE_URL, DEEPSEEK_MODEL

_HEADERS = {
    "Authorization": f"Bearer {OPENROUTER_API_KEY}",
    "Content-Type": "application/json",
    "HTTP-Referer": "https://devops-rx.onrender.com",
    "X-Title": "DevOps-Rx",
}


def chat(system: str, user: str, json_mode: bool = False) -> str:
    payload = {
        "model": DEEPSEEK_MODEL,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "max_tokens": 4096,
        "temperature": 0.2,
    }
    if json_mode:
        payload["response_format"] = {"type": "json_object"}

    resp = requests.post(
        f"{OPENROUTER_BASE_URL}/chat/completions",
        headers=_HEADERS,
        json=payload,
        timeout=120,
    )
    resp.raise_for_status()
    return resp.json()["choices"][0]["message"]["content"]


def chat_json(system: str, user: str, model_cls, retries: int = 2):
    last_err = None
    for attempt in range(retries + 1):
        raw = chat(system, user, json_mode=True)
        try:
            return model_cls(**json.loads(raw))
        except (json.JSONDecodeError, ValidationError) as e:
            last_err = e
            user = (
                f"{user}\n\n"
                f"Your previous reply was invalid ({e}). "
                f"Return ONLY valid JSON matching the required schema."
            )
    raise RuntimeError(
        f"LLM returned invalid JSON after {retries + 1} attempts"
    ) from last_err
