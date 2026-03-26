"""
Synchronous JSON REST helpers for RunningHub OpenAPI endpoints.
"""

import json
import time
from typing import Any, Dict

import requests


def _log(prefix: str, msg: str):
    print(f"[{prefix}] {msg}")


def dumps_json(data: Any) -> str:
    """Serialize data to a readable JSON string."""
    return json.dumps(data, ensure_ascii=False, indent=2)


def post_json(
    endpoint: str,
    payload: Dict[str, Any],
    api_key: str,
    base_url: str,
    timeout: int = 60,
    max_retries: int = 3,
    logger_prefix: str = "RH_OpenAPI_REST",
) -> Dict[str, Any]:
    """
    POST JSON to a synchronous RunningHub OpenAPI endpoint.

    Returns:
        Parsed JSON response when code == 0.
    """
    url = f"{base_url.rstrip('/')}/{endpoint.lstrip('/')}"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    last_error = None
    for attempt in range(max_retries):
        try:
            if attempt > 0:
                wait = min(2 ** attempt, 30)
                _log(logger_prefix, f"REST retry {attempt + 1}/{max_retries} in {wait}s...")
                time.sleep(wait)

            response = requests.post(url, headers=headers, json=payload, timeout=timeout)
        except requests.exceptions.RequestException as e:
            last_error = RuntimeError(f"Network error: {type(e).__name__}: {e}")
            _log(logger_prefix, f"Attempt {attempt + 1} network error: {type(e).__name__}")
            continue

        try:
            data = response.json() if response.text else {}
        except ValueError:
            data = None

        if response.status_code != 200:
            err_msg = (
                (data or {}).get("msg")
                or (data or {}).get("message")
                or response.text[:200]
                or f"HTTP {response.status_code}"
            )
            last_error = RuntimeError(f"HTTP {response.status_code}: {err_msg}")
            if response.status_code >= 500 or response.status_code == 429:
                _log(logger_prefix, f"Attempt {attempt + 1} HTTP {response.status_code}, retrying...")
                continue
            raise last_error

        if not isinstance(data, dict):
            raise RuntimeError(f"Invalid JSON response: {response.text[:200]}")

        if data.get("code") != 0:
            err_msg = data.get("msg") or data.get("message") or "Request failed"
            last_error = RuntimeError(str(err_msg))
            retry_text = str(err_msg).lower()
            if "server" in retry_text or "internal" in retry_text or "timeout" in retry_text:
                _log(logger_prefix, f"Attempt {attempt + 1} server-side error, retrying...")
                continue
            raise last_error

        return data

    raise RuntimeError(f"REST request failed after {max_retries} attempts: {last_error}")
