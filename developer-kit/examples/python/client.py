"""Minimal RunningHub API client for product integration examples.

This file is intentionally dependency-free so AI coding agents can copy it into
most Python products. Production systems may replace urllib with requests/httpx.
"""

from __future__ import annotations

import json
import mimetypes
import os
import time
import uuid
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Tuple, Union


DEFAULT_BASE_URL = "https://www.runninghub.cn/openapi/v2"
NON_TERMINAL_STATUSES = {"CREATE", "QUEUED", "RUNNING"}
SUCCESS_STATUS = "SUCCESS"
FAILURE_STATUSES = {"FAILED", "CANCEL"}


class RunningHubError(RuntimeError):
    """Base error for RunningHub client failures."""


class RunningHubTimeoutError(RunningHubError):
    """Raised when task polling exceeds the configured timeout."""


@dataclass
class RHResult:
    task_id: str
    outputs: List[str]
    raw_response: Dict[str, Any]


class RunningHubClient:
    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        timeout: int = 60,
        polling_interval: float = 5.0,
        max_polling_time: int = 1800,
        max_retries: int = 3,
    ) -> None:
        self.api_key = api_key or os.environ.get("RH_API_KEY", "").strip()
        self.base_url = (base_url or os.environ.get("RH_API_BASE_URL") or DEFAULT_BASE_URL).rstrip("/")
        self.timeout = timeout
        self.polling_interval = polling_interval
        self.max_polling_time = max_polling_time
        self.max_retries = max_retries
        if not self.api_key:
            raise RunningHubError("RH_API_KEY is required.")

    def run(
        self,
        endpoint: str,
        payload: Mapping[str, Any],
        local_files: Optional[Mapping[str, Union[str, Path, Iterable[Union[str, Path]]]]] = None,
    ) -> RHResult:
        """Upload local media, submit a task, poll it, and return parsed outputs."""
        prepared_payload = dict(payload)
        if local_files:
            for field_key, files in local_files.items():
                if isinstance(files, (str, Path)):
                    prepared_payload[field_key] = self.upload_file(files)
                else:
                    prepared_payload[field_key] = [self.upload_file(path) for path in files]

        task_id = self.submit(endpoint, prepared_payload)
        final_response = self.poll(task_id)
        return RHResult(
            task_id=task_id,
            outputs=extract_outputs(final_response),
            raw_response=final_response,
        )

    def upload_file(self, file_path: Union[str, Path]) -> str:
        """Upload a local media file and return its RunningHub download URL."""
        path = Path(file_path)
        if not path.is_file():
            raise RunningHubError(f"File does not exist: {path}")

        mime_type = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
        boundary = f"----rh-{uuid.uuid4().hex}"
        body = build_multipart_body(boundary, path, mime_type)
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": f"multipart/form-data; boundary={boundary}",
        }
        data = self._request_json(
            "POST",
            f"{self.base_url}/media/upload/binary",
            body=body,
            headers=headers,
            retryable=True,
        )

        if data.get("code") != 0:
            message = data.get("msg") or data.get("message") or data.get("errorMessage") or "Upload failed"
            raise RunningHubError(f"Upload failed: {message}")

        download_url = ((data.get("data") or {}).get("download_url") or "").strip()
        if not download_url:
            raise RunningHubError("Upload failed: missing data.download_url")
        return download_url

    def submit(self, endpoint: str, payload: Mapping[str, Any]) -> str:
        """Submit a model task and return taskId."""
        if not endpoint or endpoint.startswith("/"):
            raise RunningHubError("Endpoint must be a relative path without a leading slash.")

        data = self._post_json(f"{self.base_url}/{endpoint}", dict(payload), retryable=True)
        error_code = data.get("errorCode") or data.get("error_code")
        error_message = data.get("errorMessage") or data.get("error_message")
        if error_code or error_message:
            raise RunningHubError(f"Submit failed: {error_message or error_code}")

        task_id = data.get("taskId") or data.get("task_id")
        if not task_id:
            raise RunningHubError(f"Submit failed: missing taskId in response: {data}")
        return str(task_id)

    def poll(self, task_id: str) -> Dict[str, Any]:
        """Poll /query until the task reaches a terminal status."""
        start = time.time()
        consecutive_failures = 0

        while True:
            if time.time() - start > self.max_polling_time:
                raise RunningHubTimeoutError(f"Task polling timed out after {self.max_polling_time}s: {task_id}")

            time.sleep(self.polling_interval)

            try:
                data = self._post_json(
                    f"{self.base_url}/query",
                    {"taskId": task_id},
                    retryable=False,
                )
                consecutive_failures = 0
            except Exception as exc:
                consecutive_failures += 1
                if consecutive_failures >= 5:
                    raise RunningHubError(f"Polling failed repeatedly for taskId={task_id}: {exc}") from exc
                time.sleep(min(consecutive_failures * 2, 10))
                continue

            error_code = data.get("errorCode") or data.get("error_code")
            error_message = data.get("errorMessage") or data.get("error_message")
            if error_code or error_message:
                raise RunningHubError(f"Task failed: {error_message or error_code} [taskId={task_id}]")

            status = str(data.get("status") or "").strip().upper()
            if status == SUCCESS_STATUS:
                return data
            if status in FAILURE_STATUSES:
                raise RunningHubError(f"Task ended with status={status} [taskId={task_id}]")
            if status not in NON_TERMINAL_STATUSES:
                raise RunningHubError(f"Unknown task status={status} [taskId={task_id}]")

    def _post_json(self, url: str, payload: Mapping[str, Any], retryable: bool) -> Dict[str, Any]:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        return self._request_json("POST", url, body=body, headers=headers, retryable=retryable)

    def _request_json(
        self,
        method: str,
        url: str,
        body: bytes,
        headers: Mapping[str, str],
        retryable: bool,
    ) -> Dict[str, Any]:
        last_error: Optional[BaseException] = None
        attempts = self.max_retries if retryable else 1

        for attempt in range(attempts):
            if attempt > 0:
                time.sleep(min(2 ** attempt, 15))

            request = urllib.request.Request(url, data=body, headers=dict(headers), method=method)
            try:
                with urllib.request.urlopen(request, timeout=self.timeout) as response:
                    text = response.read().decode("utf-8")
                    return json.loads(text) if text else {}
            except urllib.error.HTTPError as exc:
                text = exc.read().decode("utf-8", errors="replace")
                last_error = RunningHubError(f"HTTP {exc.code}: {text[:300]}")
                if not (retryable and is_retryable_http_error(exc.code, text)):
                    raise last_error
            except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
                last_error = exc
                if not retryable:
                    raise RunningHubError(str(exc)) from exc

        raise RunningHubError(f"Request failed after {attempts} attempts: {last_error}")


def build_multipart_body(boundary: str, path: Path, mime_type: str) -> bytes:
    filename = path.name
    file_bytes = path.read_bytes()
    parts = [
        f"--{boundary}\r\n".encode("utf-8"),
        f'Content-Disposition: form-data; name="file"; filename="{filename}"\r\n'.encode("utf-8"),
        f"Content-Type: {mime_type}\r\n\r\n".encode("utf-8"),
        file_bytes,
        b"\r\n",
        f"--{boundary}--\r\n".encode("utf-8"),
    ]
    return b"".join(parts)


def extract_outputs(response: Mapping[str, Any]) -> List[str]:
    results = response.get("results") or []
    outputs: List[str] = []
    for item in results:
        if not isinstance(item, Mapping):
            continue
        value = (
            item.get("url")
            or item.get("outputUrl")
            or item.get("text")
            or item.get("content")
            or item.get("output")
        )
        if value:
            outputs.append(str(value))
    if not outputs:
        raise RunningHubError("No outputs found in final response.")
    return outputs


def is_retryable_http_error(status_code: int, body: str) -> bool:
    return status_code == 429 or status_code >= 500


def load_registry(path: Union[str, Path]) -> Dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def find_model(registry: Mapping[str, Any], endpoint: str) -> Dict[str, Any]:
    for model in registry.get("models", []):
        if model.get("endpoint") == endpoint:
            return dict(model)
    raise RunningHubError(f"Endpoint not found in registry: {endpoint}")


def validate_payload(model: Mapping[str, Any], payload: Mapping[str, Any]) -> None:
    for param in model.get("params", []):
        key = param.get("fieldKey")
        if param.get("required") and key not in payload:
            raise RunningHubError(f"Missing required parameter: {key}")
        if key in payload and param.get("type") == "LIST":
            options = set(param.get("options") or [])
            if options and str(payload[key]) not in options:
                raise RunningHubError(f"Invalid enum value for {key}: {payload[key]}")
