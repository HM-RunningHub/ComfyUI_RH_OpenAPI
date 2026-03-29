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
_REAL_PERSON_MODE_NODE_PREFIXES = {
    "RH_OpenAPI_RhartVideoSparkvideo20ImageToVideo",
    "RH_OpenAPI_RhartVideoSparkvideo20FastImageToVideo",
    "RH_OpenAPI_RhartVideoSparkvideo20MultimodalVideo",
    "RH_OpenAPI_RhartVideoSparkvideo20FastMultimodalVideo",
}


def _log(prefix: str, msg: str):
    print(f"[{prefix}] {msg}")


def _truncate_value(v, max_len: int = 200):
    """Truncate long string values for log readability."""
    s = str(v)
    return s if len(s) <= max_len else s[:max_len] + f"...({len(s)} chars)"


def _sanitize_payload(payload: dict, max_val_len: int = 200) -> dict:
    """Create a log-safe copy: truncate long values, mask sensitive fields."""
    safe = {}
    for k, v in payload.items():
        if isinstance(v, str):
            safe[k] = _truncate_value(v, max_val_len)
        elif isinstance(v, dict):
            safe[k] = _sanitize_payload(v, max_val_len)
        elif isinstance(v, list):
            safe[k] = [
                _truncate_value(item, max_val_len) if isinstance(item, str)
                else _sanitize_payload(item, max_val_len) if isinstance(item, dict)
                else item
                for item in v
            ]
        else:
            safe[k] = v
    return safe


def _supports_real_person_mode(logger_prefix: str) -> bool:
    """Return True when the node supports SparkVideo real_person_mode."""
    return str(logger_prefix or "").strip() in _REAL_PERSON_MODE_NODE_PREFIXES


def _is_real_person_rejection(err_code: Any, err_msg: str) -> bool:
    """Detect upstream real-person policy rejections for SparkVideo."""
    code = str(err_code or "").strip()
    msg = str(err_msg or "")
    msg_lower = msg.lower()
    return (
        code == "1505"
        or "photorealistic real people are prohibited" in msg_lower
        or "不支持真人" in msg
    )


def _enhance_api_error_message(err_msg: str, err_code: Any, logger_prefix: str) -> str:
    """Rewrite selected upstream errors into clearer user guidance."""
    message = str(err_msg or "").strip()
    if not message:
        return message
    if _supports_real_person_mode(logger_prefix) and _is_real_person_rejection(err_code, message):
        return (
            "This request contains restricted real-person content. For ordinary real-person "
            "content, please modify the prompt or reference image, or enable real_person_mode. "
            "If real_person_mode is already enabled and the error still appears, the reference "
            "image or video may contain a celebrity, public figure, or protected IP character, "
            "which is still not supported. | "
            "当前请求包含受限的人物内容。若为普通真人内容，请修改提示词或参考图，或开启 "
            "real_person_mode。若已开启 real_person_mode 仍报错，通常是因为参考图或视频 "
            "包含名人、公众人物或受保护的 IP 角色，这类内容仍不支持。"
        )
    return message


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

    _log(logger_prefix, f"Submit -> POST {endpoint}")
    _log(logger_prefix, f"  Payload: {json.dumps(_sanitize_payload(payload), ensure_ascii=False)}")

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
            err_msg = _enhance_api_error_message(err_msg, err_code, logger_prefix)
            last_error = RuntimeError(f"Submit failed: {err_msg} [errorCode: {err_code}]")
            if _is_retryable_error(err_msg, response.status_code):
                _log(logger_prefix, f"Submit error (attempt {attempt + 1}): {err_msg[:100]}")
                continue
            raise last_error

        err_code = data.get("errorCode") or data.get("error_code") or ""
        err_msg = data.get("errorMessage") or data.get("error_message") or ""
        if err_code or err_msg:
            err_msg = _enhance_api_error_message(err_msg, err_code, logger_prefix)
            last_error = RuntimeError(f"Submit failed: {err_msg or f'Error code {err_code}'} [errorCode: {err_code}]")
            if _is_retryable_error(err_msg):
                _log(logger_prefix, f"Submit API error (attempt {attempt + 1}): {err_msg[:100]}")
                continue
            raise last_error

        task_id = data.get("taskId") or data.get("task_id")
        if not task_id:
            _log(logger_prefix, f"  Response (no taskId): {json.dumps(data, ensure_ascii=False)[:500]}")
            raise RuntimeError("Submit failed: No task ID in response")

        _log(logger_prefix, f"  Success: taskId={task_id}")
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

    _log(logger_prefix, f"Poll -> taskId={task_id}, interval={polling_interval}s, max={max_polling_time}s")

    start_time = time.time()
    iteration = 0
    consecutive_failures = 0
    last_status = ""

    while True:
        elapsed = time.time() - start_time
        if elapsed > max_polling_time:
            detail_url = f"https://www.runninghub.cn/call-api/call-record-detail/{task_id}"
            raise RuntimeError(
                f"该任务超过{max_polling_time}s，不再实时刷新任务状态。"
                f"您可以通过 {detail_url} 继续查看任务状态，获取生成结果。 | "
                f"Task exceeded {max_polling_time}s, real-time status polling has stopped. "
                f"You can check the task status and retrieve generated results at {detail_url}"
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
            err_msg = _enhance_api_error_message(err_msg, err_code, logger_prefix)
            _log(logger_prefix, f"  Poll error response: errorCode={err_code}, errorMessage={err_msg[:200]}")
            raise RuntimeError(
                f"Task failed: {err_msg or f'Error code {err_code}'} [errorCode: {err_code}, taskId: {task_id}]"
            )

        status = (data.get("status") or "").strip().upper()

        if status != last_status:
            _log(logger_prefix, f"  Poll #{iteration}: status={status} ({int(elapsed)}s elapsed)")
            last_status = status

        if status == STATUS_SUCCESS:
            results = data.get("results") or []
            if not results:
                raise RuntimeError(f"No results in response [taskId: {task_id}]")

            urls = []
            texts = []
            for r in results:
                u = r.get("url") or r.get("outputUrl")
                if u:
                    urls.append(u)
                t = r.get("text") or r.get("content") or r.get("output")
                if t:
                    texts.append(t)

            if not urls and not texts:
                raise RuntimeError(f"No URL or text in results [taskId: {task_id}]")

            result_items = urls if urls else texts

            _log(logger_prefix, f"  Poll complete: {len(urls)} url(s), {len(texts)} text(s), {int(elapsed)}s total")
            for i, item in enumerate(result_items):
                _log(logger_prefix, f"    result[{i}]: {_truncate_value(item, 300)}")

            if on_progress:
                try:
                    on_progress(100)
                except Exception:
                    pass
            return result_items, data

        if status == STATUS_FAILED:
            err_msg = _enhance_api_error_message(err_msg, err_code, logger_prefix)
            _log(logger_prefix, f"  Task FAILED: {err_msg or 'no message'} [errorCode: {err_code}]")
            _log(logger_prefix, f"  Full response: {json.dumps(data, ensure_ascii=False)[:500]}")
            raise RuntimeError(
                f"Task failed: {err_msg or 'Task failed'} [errorCode: {err_code}, taskId: {task_id}]"
            )

        if status == STATUS_CANCEL:
            _log(logger_prefix, f"  Task CANCELLED")
            raise RuntimeError(f"Task was cancelled [taskId: {task_id}]")

        if status and status not in (STATUS_CREATE, STATUS_QUEUED, STATUS_RUNNING):
            raise RuntimeError(f"Unknown status: {status} [taskId: {task_id}]")
