"""
Task submit and poll.

submit: POST {base_url}/{endpoint}
poll:   POST {base_url}/query
"""

import time
import json
import requests
from typing import Optional, List, Callable, Any, Dict, Tuple

# Status values (case-insensitive)
STATUS_SUCCESS = "SUCCESS"
STATUS_FAILED = "FAILED"
STATUS_CANCEL = "CANCEL"
STATUS_RUNNING = "RUNNING"
STATUS_QUEUED = "QUEUED"
STATUS_CREATE = "CREATE"

MAX_CONSECUTIVE_POLL_FAILURES = 5


def _log(prefix: str, msg: str):
    print(f"[{prefix}] {msg}")


MAX_SUBMIT_RETRIES = 3


def _is_retryable_error(error_msg: str, status_code: int = 0) -> bool:
    """Check if an error is transient and worth retrying."""
    err_lower = str(error_msg).lower()

    # Business errors: never retry
    non_retryable = [
        "violation", "illegal", "forbidden", "nsfw",
        "content policy", "unauthorized", "bad request",
        "content verification failed", "moderation",
        "invalid parameter", "parameter error",
        "balance", "insufficient", "quota",
    ]
    if any(kw in err_lower for kw in non_retryable):
        return False

    # 4xx client errors: don't retry (except 429 rate limit)
    if status_code and 400 <= status_code < 500 and status_code != 429:
        return False

    return True


def submit(
    endpoint: str,
    payload: dict,
    api_key: str,
    base_url: str,
    timeout: int = 60,
    max_retries: int = MAX_SUBMIT_RETRIES,
    logger_prefix: str = "RH_OpenAPI_Task",
) -> str:
    """
    Submit task with retry on transient errors.

    Retries on: network errors, HTTP 5xx, 429 rate limit.
    Does NOT retry on: 4xx client errors, business errors (content moderation, etc.)

    Returns:
        task_id
    """
    url = f"{base_url.rstrip('/')}/{endpoint}"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}",
    }

    last_error = None
    for attempt in range(max_retries):
        if attempt > 0:
            wait = min(2 ** attempt + 1, 15)
            _log(logger_prefix, f"Submit retry {attempt + 1}/{max_retries} in {wait}s...")
            time.sleep(wait)

        try:
            response = requests.post(url, headers=headers, json=payload, timeout=timeout)
        except requests.exceptions.RequestException as e:
            last_error = RuntimeError(f"Submit failed: Network error ({type(e).__name__}: {e})")
            _log(logger_prefix, f"Submit network error (attempt {attempt + 1}): {type(e).__name__}")
            continue

        try:
            data = response.json() if response.text else {}
        except json.JSONDecodeError:
            if response.status_code != 200:
                last_error = RuntimeError(
                    f"Submit failed: HTTP {response.status_code} [errorCode: , errorMessage: {response.text[:200]}]"
                )
                if _is_retryable_error("", response.status_code):
                    _log(logger_prefix, f"Submit HTTP {response.status_code} (attempt {attempt + 1}), retrying...")
                    continue
                raise last_error
            last_error = RuntimeError("Submit failed: Invalid JSON response")
            continue

        if response.status_code != 200:
            err_code = str(data.get("errorCode", ""))
            err_msg = data.get("errorMessage", response.text[:200]) or f"HTTP {response.status_code}"
            last_error = RuntimeError(f"Submit failed: {err_msg} [errorCode: {err_code}]")
            if _is_retryable_error(err_msg, response.status_code):
                _log(logger_prefix, f"Submit error (attempt {attempt + 1}): {err_msg[:100]}")
                continue
            raise last_error

        err_code = data.get("errorCode") or data.get("error_code") or ""
        err_msg = data.get("errorMessage") or data.get("error_message") or ""
        if err_code or err_msg:
            last_error = RuntimeError(f"Submit failed: {err_msg or f'Error code {err_code}'} [errorCode: {err_code}]")
            if _is_retryable_error(err_msg):
                _log(logger_prefix, f"Submit API error (attempt {attempt + 1}): {err_msg[:100]}")
                continue
            raise last_error

        task_id = data.get("taskId") or data.get("task_id")
        if not task_id:
            raise RuntimeError("Submit failed: No task ID in response")

        return str(task_id)

    raise last_error or RuntimeError(f"Submit failed after {max_retries} attempts")


def poll(
    task_id: str,
    api_key: str,
    base_url: str,
    polling_interval: float = 5,
    max_polling_time: int = 600,
    on_progress: Optional[Callable[[int], None]] = None,
    logger_prefix: str = "RH_OpenAPI_Task",
) -> Tuple[List[str], Dict]:
    """
    Poll task result.

    Returns:
        (result_urls, full_response) - URLs and the complete final API response dict
    """
    url = f"{base_url.rstrip('/')}/query"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}",
    }
    payload = {"taskId": task_id}

    start_time = time.time()
    iteration = 0
    consecutive_failures = 0

    while True:
        elapsed = time.time() - start_time
        if elapsed > max_polling_time:
            raise RuntimeError(
                f"Polling timeout after {max_polling_time}s [taskId: {task_id}]"
            )

        if on_progress:
            progress = min(int(30 + elapsed / max_polling_time * 55), 85)
            try:
                on_progress(progress)
            except Exception:
                pass

        time.sleep(polling_interval)
        iteration += 1

        try:
            response = requests.post(url, headers=headers, json=payload, timeout=30)
        except requests.exceptions.RequestException as e:
            consecutive_failures += 1
            _log(logger_prefix, f"Poll failed ({consecutive_failures}/{MAX_CONSECUTIVE_POLL_FAILURES}): {type(e).__name__}")
            if consecutive_failures >= MAX_CONSECUTIVE_POLL_FAILURES:
                raise RuntimeError(
                    f"Polling failed after multiple network errors [taskId: {task_id}]"
                )
            time.sleep(min(consecutive_failures * 2, 10))
            continue

        if response.status_code != 200:
            consecutive_failures += 1
            _log(logger_prefix, f"Poll HTTP {response.status_code} ({consecutive_failures}/{MAX_CONSECUTIVE_POLL_FAILURES})")
            if consecutive_failures >= MAX_CONSECUTIVE_POLL_FAILURES:
                raise RuntimeError(
                    f"Polling failed: server returned HTTP {response.status_code} "
                    f"{consecutive_failures} times consecutively [taskId: {task_id}]"
                )
            time.sleep(min(consecutive_failures * 2, 10))
            continue

        try:
            data = response.json()
        except json.JSONDecodeError:
            consecutive_failures += 1
            _log(logger_prefix, f"Poll JSON parse error ({consecutive_failures}/{MAX_CONSECUTIVE_POLL_FAILURES})")
            if consecutive_failures >= MAX_CONSECUTIVE_POLL_FAILURES:
                raise RuntimeError(
                    f"Polling failed: invalid JSON response "
                    f"{consecutive_failures} times consecutively [taskId: {task_id}]"
                )
            continue

        consecutive_failures = 0

        err_code = data.get("errorCode") or data.get("error_code") or ""
        err_msg = data.get("errorMessage") or data.get("error_message") or ""
        if err_code or err_msg:
            raise RuntimeError(
                f"Task failed: {err_msg or f'Error code {err_code}'} [errorCode: {err_code}, taskId: {task_id}]"
            )

        status = (data.get("status") or "").strip().upper()

        if status == STATUS_SUCCESS:
            results = data.get("results") or []
            if not results:
                raise RuntimeError(f"No results in response [taskId: {task_id}]")

            urls = []
            for r in results:
                u = r.get("url") or r.get("outputUrl")
                if u:
                    urls.append(u)
            if not urls:
                raise RuntimeError(f"No URL in results [taskId: {task_id}]")

            if on_progress:
                try:
                    on_progress(100)
                except Exception:
                    pass
            return urls, data

        if status == STATUS_FAILED:
            raise RuntimeError(
                f"Task failed: {err_msg or 'Task failed'} [errorCode: {err_code}, taskId: {task_id}]"
            )

        if status == STATUS_CANCEL:
            raise RuntimeError(f"Task was cancelled [taskId: {task_id}]")

        if status and status not in (STATUS_CREATE, STATUS_QUEUED, STATUS_RUNNING):
            raise RuntimeError(f"Unknown status: {status} [taskId: {task_id}]")
