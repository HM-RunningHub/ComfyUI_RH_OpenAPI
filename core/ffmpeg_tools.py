"""
ffmpeg / ffprobe discovery with local cache and optional Windows auto-download.
"""

from __future__ import annotations

from functools import lru_cache
import os
from pathlib import Path
import shutil
import sys
import tempfile
import threading
import zipfile

import requests

_TOOL_NAMES = {"ffmpeg", "ffprobe"}
_DOWNLOAD_URLS = [
    "https://github.com/GyanD/codexffmpeg/releases/download/8.1/ffmpeg-8.1-essentials_build.zip",
    "https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip",
]
_DOWNLOAD_URL_ENV = "RH_FFMPEG_DOWNLOAD_URL"
_CACHE_DIR_ENV = "RH_FFMPEG_CACHE_DIR"
_DISABLE_AUTO_DOWNLOAD_ENV = "RH_DISABLE_AUTO_FFMPEG_DOWNLOAD"
_RESOLUTION_LOCK = threading.Lock()
_RESOLVED_TOOLS: dict[str, str] = {}


def _plugin_root() -> Path:
    return Path(__file__).resolve().parent.parent


@lru_cache(maxsize=1)
def _load_plugin_env() -> dict[str, str]:
    env_path = _plugin_root() / "config" / ".env"
    result: dict[str, str] = {}
    if not env_path.exists():
        return result

    try:
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, _, value = line.partition("=")
                    key = key.strip()
                    value = value.strip().strip('"').strip("'")
                    if key and value:
                        result[key] = value
    except Exception:
        pass
    return result


def _get_setting(name: str) -> str:
    value = (os.environ.get(name) or "").strip()
    if value:
        return value
    return (_load_plugin_env().get(name) or "").strip()


def _normalize_tool_name(tool_name: str) -> str:
    normalized = str(tool_name or "").strip().lower()
    if normalized not in _TOOL_NAMES:
        raise ValueError(f"Unsupported video tool: {tool_name}")
    return normalized


def _binary_name(tool_name: str) -> str:
    normalized = _normalize_tool_name(tool_name)
    suffix = ".exe" if os.name == "nt" else ""
    return f"{normalized}{suffix}"


def _is_truthy(value: str) -> bool:
    return str(value or "").strip().lower() in {"1", "true", "yes", "on"}


def _default_cache_dir() -> Path:
    if os.name == "nt":
        base_dir = os.environ.get("LOCALAPPDATA") or os.environ.get("APPDATA")
        if base_dir:
            return Path(base_dir) / "ComfyUI_RH_OpenAPI" / "ffmpeg"

    home = Path.home()
    if sys.platform == "darwin":
        return home / "Library" / "Caches" / "ComfyUI_RH_OpenAPI" / "ffmpeg"

    xdg_cache = os.environ.get("XDG_CACHE_HOME")
    if xdg_cache:
        return Path(xdg_cache) / "ComfyUI_RH_OpenAPI" / "ffmpeg"

    if home.exists():
        return home / ".cache" / "ComfyUI_RH_OpenAPI" / "ffmpeg"

    return Path(tempfile.gettempdir()) / "ComfyUI_RH_OpenAPI" / "ffmpeg"


def _cache_dir() -> Path:
    raw_value = _get_setting(_CACHE_DIR_ENV)
    if raw_value:
        return Path(os.path.expandvars(os.path.expanduser(raw_value)))
    return _default_cache_dir()


def _is_usable_binary(path: Path) -> bool:
    try:
        return path.is_file() and path.stat().st_size > 0
    except OSError:
        return False


def _resolve_path_candidate(raw_value: str, tool_name: str) -> str | None:
    text = str(raw_value or "").strip().strip('"').strip("'")
    if not text:
        return None

    which_match = shutil.which(text)
    if which_match:
        return which_match

    candidate = Path(os.path.expandvars(os.path.expanduser(text)))
    candidates = []
    if candidate.is_dir():
        candidates.append(candidate / _binary_name(tool_name))
    else:
        candidates.append(candidate)
        candidates.append(candidate.with_name(_binary_name(tool_name)))

    for item in candidates:
        if _is_usable_binary(item):
            return str(item)
    return None


def _resolve_from_override(tool_name: str) -> str | None:
    specific_setting = f"RH_{tool_name.upper()}_PATH"
    specific_value = _get_setting(specific_setting)
    if specific_value:
        resolved = _resolve_path_candidate(specific_value, tool_name)
        if not resolved:
            raise RuntimeError(
                f"{specific_setting} is set but {tool_name} was not found at: {specific_value}"
            )
        return resolved

    sibling_setting = "RH_FFPROBE_PATH" if tool_name == "ffmpeg" else "RH_FFMPEG_PATH"
    sibling_value = _get_setting(sibling_setting)
    if sibling_value:
        return _resolve_path_candidate(sibling_value, tool_name)
    return None


def _resolve_from_cache(tool_name: str) -> str | None:
    candidate = _cache_dir() / _binary_name(tool_name)
    if _is_usable_binary(candidate):
        return str(candidate)
    return None


def _safe_extract_zip(archive_path: Path, destination: Path):
    destination.mkdir(parents=True, exist_ok=True)
    destination_root = destination.resolve()
    with zipfile.ZipFile(archive_path) as zip_file:
        for member in zip_file.infolist():
            target_path = (destination / member.filename).resolve()
            if os.path.commonpath([str(destination_root), str(target_path)]) != str(destination_root):
                raise RuntimeError(f"Unexpected path inside FFmpeg archive: {member.filename}")
        zip_file.extractall(destination)


def _find_extracted_binary(extract_dir: Path, tool_name: str) -> Path:
    binary_name = _binary_name(tool_name)
    matches = sorted(extract_dir.rglob(binary_name))
    for match in matches:
        if _is_usable_binary(match):
            return match
    raise RuntimeError(f"Downloaded FFmpeg archive does not contain {binary_name}")


def _get_download_urls() -> list[str]:
    custom_url = _get_setting(_DOWNLOAD_URL_ENV)
    if custom_url:
        return [custom_url]
    return list(_DOWNLOAD_URLS)


def _download_from_url(url: str, archive_path: Path):
    with requests.get(url, stream=True, timeout=(15, 300)) as response:
        response.raise_for_status()
        with open(archive_path, "wb") as f:
            for chunk in response.iter_content(chunk_size=1024 * 1024):
                if chunk:
                    f.write(chunk)


def _download_windows_release(archive_path: Path):
    urls = _get_download_urls()
    last_error: Exception | None = None
    for i, url in enumerate(urls):
        try:
            print(f"[RH_OpenAPI] Trying download source {i + 1}/{len(urls)}: {url}")
            _download_from_url(url, archive_path)
            print(f"[RH_OpenAPI] Download completed from: {url}")
            return
        except Exception as e:
            last_error = e
            print(f"[RH_OpenAPI] Download source {i + 1} failed: {e}")
            if archive_path.exists():
                try:
                    archive_path.unlink()
                except OSError:
                    pass
    raise RuntimeError(
        f"All {len(urls)} download sources failed. Last error: {last_error}. "
        f"You can set {_DOWNLOAD_URL_ENV} to a custom mirror URL, or manually place "
        f"ffmpeg.exe and ffprobe.exe in the cache directory and set RH_FFMPEG_PATH to it."
    )


def _install_windows_tools_to_cache(cache_dir: Path):
    ffmpeg_target = cache_dir / _binary_name("ffmpeg")
    ffprobe_target = cache_dir / _binary_name("ffprobe")
    if _is_usable_binary(ffmpeg_target) and _is_usable_binary(ffprobe_target):
        return

    cache_dir.mkdir(parents=True, exist_ok=True)
    temp_root = Path(tempfile.mkdtemp(prefix="rh_ffmpeg_download_"))
    staging_dir = cache_dir / ".installing"

    print(
        "[RH_OpenAPI] ffmpeg/ffprobe not found; downloading a portable FFmpeg build "
        f"into local cache: {cache_dir}"
    )

    try:
        archive_path = temp_root / "ffmpeg-release-essentials.zip"
        extract_dir = temp_root / "extract"
        _download_windows_release(archive_path)
        _safe_extract_zip(archive_path, extract_dir)

        if staging_dir.exists():
            shutil.rmtree(staging_dir, ignore_errors=True)
        staging_dir.mkdir(parents=True, exist_ok=True)

        for tool_name in ("ffmpeg", "ffprobe"):
            source_path = _find_extracted_binary(extract_dir, tool_name)
            staged_path = staging_dir / _binary_name(tool_name)
            shutil.copy2(source_path, staged_path)
            os.replace(staged_path, cache_dir / _binary_name(tool_name))

        metadata_path = cache_dir / "source.txt"
        with open(metadata_path, "w", encoding="utf-8") as f:
            f.write("download_urls: " + ", ".join(_get_download_urls()) + "\n")

        print("[RH_OpenAPI] Portable FFmpeg tools are ready.")
    except Exception as e:
        raise RuntimeError(f"automatic FFmpeg download failed: {e}") from e
    finally:
        shutil.rmtree(temp_root, ignore_errors=True)
        shutil.rmtree(staging_dir, ignore_errors=True)


def _missing_tool_error(tool_name: str, detail: str | None = None) -> RuntimeError:
    base_message = f"{tool_name} is required to preprocess VIDEO assets."
    if detail:
        base_message += f" {detail}"

    base_message += (
        " Set RH_FFMPEG_PATH / RH_FFPROBE_PATH to an executable or bin directory, "
        "or install ffmpeg/ffprobe in the ComfyUI runtime PATH."
    )

    if os.name == "nt":
        base_message += (
            " On Windows, the public main branch can also auto-download a portable build "
            f"into {_cache_dir()} unless {_DISABLE_AUTO_DOWNLOAD_ENV}=1 is set."
        )

    return RuntimeError(base_message)


def resolve_video_tool_path(tool_name: str) -> str:
    normalized = _normalize_tool_name(tool_name)
    cached_path = _RESOLVED_TOOLS.get(normalized)
    if cached_path and _is_usable_binary(Path(cached_path)):
        return cached_path

    with _RESOLUTION_LOCK:
        cached_path = _RESOLVED_TOOLS.get(normalized)
        if cached_path and _is_usable_binary(Path(cached_path)):
            return cached_path

        override_path = _resolve_from_override(normalized)
        if override_path:
            _RESOLVED_TOOLS[normalized] = override_path
            return override_path

        cache_path = _resolve_from_cache(normalized)
        if cache_path:
            _RESOLVED_TOOLS[normalized] = cache_path
            return cache_path

        system_path = shutil.which(normalized)
        if system_path:
            _RESOLVED_TOOLS[normalized] = system_path
            return system_path

        if os.name == "nt" and not _is_truthy(_get_setting(_DISABLE_AUTO_DOWNLOAD_ENV)):
            try:
                _install_windows_tools_to_cache(_cache_dir())
            except RuntimeError as e:
                raise _missing_tool_error(normalized, f"Automatic setup failed: {e}.") from e

            cache_path = _resolve_from_cache(normalized)
            if cache_path:
                _RESOLVED_TOOLS[normalized] = cache_path
                return cache_path

        raise _missing_tool_error(normalized)
