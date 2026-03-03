"""
Config and API key resolution.

Priority: Settings (valid) > PromptServer shared_api_key > env vars > config/.env.
Settings valid when both base_url and apiKey are non-empty.
"""

import os
from pathlib import Path
from typing import Optional, Dict, Any

# Default values when env/config do not set RH_API_* or RH_UPLOAD_*
DEFAULT_TIMEOUT = 60
DEFAULT_POLLING_INTERVAL = 5.0
DEFAULT_MAX_POLLING_TIME = 600
DEFAULT_UPLOAD_TIMEOUT = 60
DEFAULT_BASE_URL = "https://www.runninghub.cn/openapi/v2"


def _get_plugin_root() -> Path:
    """Return plugin root directory."""
    return Path(__file__).resolve().parent.parent


def _load_from_env() -> Dict[str, str]:
    """Load key=value pairs from config/.env."""
    env_path = _get_plugin_root() / "config" / ".env"
    result = {}
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


def _extract_config(api_config: Any) -> Optional[Dict]:
    """Extract config from Settings node STRUCT (ComfyUI_RH_APICall format)."""
    if api_config is None:
        return None
    if isinstance(api_config, list) and len(api_config) > 0:
        item = api_config[0]
        if isinstance(item, dict):
            return item
    if isinstance(api_config, dict):
        return api_config
    return None


def _get_shared_api_key() -> Optional[str]:
    """Try to get shared API key from PromptServer instance (RunningHub system default)."""
    try:
        from server import PromptServer
        instance = PromptServer.instance
        api_key = getattr(instance, 'shared_api_key', None)
        if api_key and isinstance(api_key, str) and api_key.strip() and api_key != 'unknown':
            return api_key.strip()
    except Exception:
        pass
    return None


def _build_config(base_url: str, api_key: str, env_data: Dict[str, str]) -> Dict[str, Any]:
    """Build a config dict from base_url, api_key, and env_data."""
    return {
        "base_url": base_url.rstrip("/"),
        "api_key": api_key,
        "timeout": int(env_data.get("RH_API_TIMEOUT", DEFAULT_TIMEOUT)),
        "polling_interval": float(env_data.get("RH_API_POLLING_INTERVAL", DEFAULT_POLLING_INTERVAL)),
        "max_polling_time": int(env_data.get("RH_API_MAX_POLLING_TIME", DEFAULT_MAX_POLLING_TIME)),
        "upload_timeout": int(env_data.get("RH_UPLOAD_TIMEOUT", DEFAULT_UPLOAD_TIMEOUT)),
    }


def get_config(api_config: Any = None) -> Dict[str, Any]:
    """
    Resolve config: base_url, api_key
    Priority: (1) Settings node, (2) PromptServer shared_api_key, (3) env vars, (4) config/.env.
    """
    env_data = _load_from_env()

    # Priority 1: Settings node (api_config connected)
    if api_config is not None:
        c = _extract_config(api_config)
        if c:
            base_url = (c.get("base_url") or "").strip()
            api_key = (c.get("apiKey") or c.get("api_key") or "").strip()
            if base_url and api_key:
                return _build_config(base_url, api_key, env_data)
            raise RuntimeError("Settings: both base_url and apiKey are required.")

    # Priority 2: PromptServer shared_api_key (RunningHub system default)
    shared_key = _get_shared_api_key()
    if shared_key:
        print(f"[RH_OpenAPI] Using system shared_api_key: ...{shared_key[-6:]}")
        return _build_config(DEFAULT_BASE_URL, shared_key, env_data)

    # Priority 3: Environment variables
    base_url = (os.environ.get("RH_API_BASE_URL") or "").strip()
    api_key = (os.environ.get("RH_API_KEY") or "").strip()
    if base_url and api_key:
        return _build_config(base_url, api_key, {
            **env_data,
            "RH_API_TIMEOUT": env_data.get("RH_API_TIMEOUT", os.environ.get("RH_API_TIMEOUT", str(DEFAULT_TIMEOUT))),
            "RH_API_POLLING_INTERVAL": env_data.get("RH_API_POLLING_INTERVAL", os.environ.get("RH_API_POLLING_INTERVAL", str(DEFAULT_POLLING_INTERVAL))),
            "RH_API_MAX_POLLING_TIME": env_data.get("RH_API_MAX_POLLING_TIME", os.environ.get("RH_API_MAX_POLLING_TIME", str(DEFAULT_MAX_POLLING_TIME))),
            "RH_UPLOAD_TIMEOUT": env_data.get("RH_UPLOAD_TIMEOUT", os.environ.get("RH_UPLOAD_TIMEOUT", str(DEFAULT_UPLOAD_TIMEOUT))),
        })

    # Priority 4: config/.env file
    base_url = base_url or (env_data.get("RH_API_BASE_URL") or "").strip()
    api_key = api_key or (env_data.get("RH_API_KEY") or "").strip()

    if not api_key:
        raise RuntimeError(
            "RH API key is required. Set RH_API_KEY in env or config/.env, or connect Settings node."
        )
    if not base_url:
        raise RuntimeError(
            "RH base URL is required. Set RH_API_BASE_URL in env or config/.env, or connect Settings node."
        )

    return _build_config(base_url, api_key, env_data)
