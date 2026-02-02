"""
File upload - POST /media/upload/binary.

Supports image, audio, video.
"""

import time
import requests
from typing import List, Union, Any, Optional
from io import BytesIO

from .api_key import get_config


def _log(prefix: str, msg: str):
    print(f"[{prefix}] {msg}")


def upload_file(
    file_content: Union[bytes, BytesIO],
    filename: str,
    mime_type: str,
    api_key: str,
    base_url: str,
    timeout: int = 60,
    max_retries: int = 3,
    logger_prefix: str = "RH_OpenAPI_Upload",
) -> str:
    """
    Upload a single file to /media/upload/binary.

    Returns:
        download_url from data.download_url
    """
    url = f"{base_url.rstrip('/')}/media/upload/binary"
    headers = {"Authorization": f"Bearer {api_key}"}

    if isinstance(file_content, BytesIO):
        file_content = file_content.getvalue()

    files = {"file": (filename, file_content, mime_type)}

    last_error = None
    for attempt in range(max_retries):
        try:
            if attempt > 0:
                wait = min(2 ** attempt, 30)
                _log(logger_prefix, f"Retry {attempt + 1}/{max_retries} in {wait}s...")
                time.sleep(wait)

            response = requests.post(url, headers=headers, files=files, timeout=timeout)
            data = response.json() if response.text else {}

            if response.status_code != 200:
                err_msg = data.get("message", response.text[:200])
                raise RuntimeError(f"HTTP {response.status_code}: {err_msg}")

            if data.get("code") != 0:
                raise RuntimeError(data.get("message", "Upload failed"))

            download_url = (data.get("data") or {}).get("download_url")
            if not download_url:
                raise RuntimeError("No download_url in response")

            return download_url

        except requests.exceptions.RequestException as e:
            last_error = e
            _log(logger_prefix, f"Attempt {attempt + 1} failed: {e}")
            continue

    raise RuntimeError(f"Upload failed after {max_retries} attempts: {last_error}")


def upload_files(
    file_list: List[tuple],
    api_key: str,
    base_url: str,
    timeout: int = 60,
    max_retries: int = 3,
    logger_prefix: str = "RH_OpenAPI_Upload",
) -> List[str]:
    """
    Upload multiple files.

    Args:
        file_list: [(file_content, filename, mime_type), ...]

    Returns:
        [url1, url2, ...]
    """
    urls = []
    for content, filename, mime_type in file_list:
        url = upload_file(
            content, filename, mime_type, api_key, base_url, timeout, max_retries, logger_prefix
        )
        urls.append(url)
    return urls
