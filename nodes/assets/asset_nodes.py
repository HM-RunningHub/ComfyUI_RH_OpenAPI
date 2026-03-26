"""
SparkVideo asset management nodes.
"""

import os
import re
import time

from ...core.audio import audio_to_bytes
from ...core.image import tensor_to_bytes
from ...core.rest import dumps_json, post_json
from ...core.upload import upload_file
from .base import AssetRestNodeBase, clean_string, connectable_string_input, text_input


FIXED_ASSET_GROUP_ID = "group-20260327004931-dvjbj"
FIXED_ASSET_NAME = "RHas01"
ASSET_READY_STATUSES = {"ACTIVE", "SUCCESS", "SUCCEEDED", "COMPLETED", "DONE", "READY", "AVAILABLE"}
ASSET_FAILED_STATUSES = {"FAILED", "ERROR", "CANCEL", "CANCELED"}
ASSET_READY_TIMEOUTS = {
    "image": 60,
    "video": 180,
    "audio": 60,
}


def _video_to_bytes(value) -> bytes:
    if hasattr(value, "get_stream_source"):
        source = value.get_stream_source()
        if isinstance(source, str) and os.path.isfile(source):
            with open(source, "rb") as f:
                return f.read()
        if hasattr(source, "read"):
            return source.read()

    if hasattr(value, "path") and os.path.isfile(value.path):
        with open(value.path, "rb") as f:
            return f.read()

    if hasattr(value, "file_path") and os.path.isfile(value.file_path):
        with open(value.file_path, "rb") as f:
            return f.read()

    if isinstance(value, dict):
        file_path = value.get("file_path") or value.get("path")
        if file_path and os.path.isfile(file_path):
            with open(file_path, "rb") as f:
                return f.read()

    if isinstance(value, str) and os.path.isfile(value):
        with open(value, "rb") as f:
            return f.read()

    raise ValueError(f"Could not extract video bytes from {type(value).__name__}")


def _normalize_asset_media_type(media_type: str) -> str:
    """Normalize media type to the asset API values."""
    value = str(media_type or "").strip().lower()
    mapping = {
        "image": "Image",
        "video": "Video",
        "audio": "Audio",
    }
    normalized = mapping.get(value)
    if not normalized:
        raise ValueError(f"Unsupported asset media type: {media_type}")
    return normalized


def _query_asset_info(asset_id: str, config, logger_prefix: str) -> dict:
    """Query asset metadata from the asset service."""
    response = post_json(
        "assets/query",
        {"assetId": asset_id},
        config["api_key"],
        config["base_url"],
        timeout=config.get("timeout", 60),
        max_retries=1,
        logger_prefix=f"{logger_prefix}_AssetQuery",
    )
    data = response.get("data") or {}
    return {
        "asset_id": clean_string(data.get("assetId")) or asset_id,
        "status": clean_string(data.get("status")),
        "preview_url": clean_string(data.get("previewUrl")),
        "asset_type": clean_string(data.get("assetType")),
        "response": response,
    }


def _asset_ready_timeout(config, media_type: str) -> int:
    """Resolve asset readiness timeout with media-aware defaults."""
    default_timeout = ASSET_READY_TIMEOUTS.get(str(media_type or "").strip().lower(), 90)
    custom_timeout = config.get("asset_ready_timeout")
    if custom_timeout is None:
        return default_timeout
    try:
        return max(5, int(custom_timeout))
    except (TypeError, ValueError):
        return default_timeout


def wait_for_asset_ready(asset_id: str, config, media_type: str, logger_prefix: str) -> dict:
    """Poll asset status until the asset is ready to be consumed."""
    timeout_seconds = _asset_ready_timeout(config, media_type)
    poll_interval = max(1, int(config.get("asset_ready_poll_interval", 2)))
    deadline = time.time() + timeout_seconds
    consecutive_failures = 0
    max_consecutive_failures = 5
    last_status = None

    while True:
        try:
            asset_info = _query_asset_info(asset_id, config, logger_prefix)
        except Exception as e:
            consecutive_failures += 1
            print(
                f"[{logger_prefix}] WARNING: asset readiness poll failed "
                f"({consecutive_failures}/{max_consecutive_failures}): {e}"
            )
            if consecutive_failures >= max_consecutive_failures:
                raise RuntimeError(f"Asset {asset_id} readiness polling failed: {e}") from e
            if time.time() >= deadline:
                raise RuntimeError(f"Timed out while waiting for asset {asset_id} to become ready") from e
            time.sleep(min(consecutive_failures * 2, 10))
            continue

        consecutive_failures = 0
        status = clean_string(asset_info.get("status")).upper()
        if status != last_status:
            print(f"[{logger_prefix}] Asset {asset_id} status={status or 'UNKNOWN'}")
            last_status = status

        if status in ASSET_READY_STATUSES:
            return asset_info

        if status in ASSET_FAILED_STATUSES:
            raise RuntimeError(f"Asset {asset_id} processing failed with status: {status}")

        if time.time() >= deadline:
            raise RuntimeError(
                f"Timed out after {timeout_seconds}s waiting for asset {asset_id} to become ready "
                f"(last status: {status or 'unknown'})"
            )

        time.sleep(poll_interval)


def _upload_media_for_asset(config, media_type: str, media_value, logger_prefix: str) -> dict:
    """Upload local media and return the fixed asset payload parts."""
    asset_type = _normalize_asset_media_type(media_type)

    if asset_type == "Image":
        file_bytes = tensor_to_bytes(media_value)
        filename = f"asset_{abs(hash(file_bytes)) % 10**10}.png"
        mime_type = "image/png"
        upload_timeout = config.get("upload_timeout", 60)
    elif asset_type == "Video":
        file_bytes = _video_to_bytes(media_value)
        filename = f"asset_{abs(hash(file_bytes)) % 10**10}.mp4"
        mime_type = "video/mp4"
        upload_timeout = max(config.get("upload_timeout", 60), 120)
    else:
        if not isinstance(media_value, dict) or "waveform" not in media_value:
            raise ValueError("audio input must be a valid ComfyUI AUDIO value")
        file_bytes = audio_to_bytes(media_value)
        filename = f"asset_{abs(hash(file_bytes)) % 10**10}.wav"
        mime_type = "audio/wav"
        upload_timeout = config.get("upload_timeout", 60)

    source_url = upload_file(
        file_bytes,
        filename,
        mime_type,
        config["api_key"],
        config["base_url"],
        timeout=upload_timeout,
        logger_prefix=logger_prefix,
    )
    return {
        "groupId": FIXED_ASSET_GROUP_ID,
        "url": source_url,
        "assetType": asset_type,
        "name": FIXED_ASSET_NAME,
    }


def prepare_fixed_asset_create_payload(config, media_type: str, media_value, logger_prefix: str) -> dict:
    """Prepare a fixed asset-create payload from local media."""
    return _upload_media_for_asset(config, media_type, media_value, logger_prefix)


def create_fixed_asset_from_media(config, media_type: str, media_value, logger_prefix: str) -> dict:
    """Create a fixed asset from local media and return asset metadata."""
    payload = prepare_fixed_asset_create_payload(config, media_type, media_value, logger_prefix)
    response = post_json(
        "assets/create",
        payload,
        config["api_key"],
        config["base_url"],
        timeout=config.get("timeout", 60),
        logger_prefix=f"{logger_prefix}_AssetCreate",
    )
    data = response.get("data") or {}
    asset_id = clean_string(data.get("assetId"))
    if not asset_id:
        raise RuntimeError("No assetId returned from asset create API")
    ready_info = wait_for_asset_ready(
        asset_id,
        config,
        media_type,
        f"{logger_prefix}_AssetReady",
    )
    return {
        "asset_id": asset_id,
        "asset_url": f"asset://{asset_id}",
        "status": clean_string(ready_info.get("status")) or clean_string(data.get("status")),
        "response": ready_info.get("response") or response,
    }


def _split_asset_ids(*values) -> list:
    """Flatten raw asset id inputs into a clean ordered list."""
    result = []
    for value in values:
        if value is None:
            continue
        text = str(value).strip()
        if not text:
            continue
        parts = re.split(r"[\n,]+", text)
        for part in parts:
            asset_id = clean_string(part)
            if not asset_id:
                continue
            if asset_id.startswith("asset://"):
                asset_id = asset_id[8:]
            result.append(asset_id)
    return result


class RH_SparkVideoAssetCreate(AssetRestNodeBase):
    ENDPOINT = "assets/create"
    RETURN_TYPES = ("STRING", "STRING", "STRING")
    RETURN_NAMES = ("asset_id", "status", "response")

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {},
            "optional": {
                "image": ("IMAGE",),
                "video": ("VIDEO",),
                "audio": ("AUDIO",),
                **cls.common_optional_inputs(),
            },
        }

    def prepare_payload(self, config, image=None, video=None, audio=None, **kwargs):
        media_inputs = []
        if image is not None:
            media_inputs.append(("Image", image))
        if video is not None:
            media_inputs.append(("Video", video))
        if audio is not None:
            media_inputs.append(("Audio", audio))

        if len(media_inputs) != 1:
            raise ValueError("Exactly one of image, video, or audio must be provided")

        asset_type, media_value = media_inputs[0]
        return prepare_fixed_asset_create_payload(config, asset_type, media_value, self._log_prefix)

    def parse_response(self, response, config=None, image=None, video=None, audio=None, **kwargs):
        data = response.get("data") or {}
        asset_id = clean_string(data.get("assetId"))
        status = clean_string(data.get("status"))
        final_response = response

        media_type = ""
        if image is not None:
            media_type = "image"
        elif video is not None:
            media_type = "video"
        elif audio is not None:
            media_type = "audio"

        if config is not None and asset_id:
            ready_info = wait_for_asset_ready(
                asset_id,
                config,
                media_type,
                f"{self._log_prefix}_AssetReady",
            )
            status = clean_string(ready_info.get("status")) or status
            final_response = ready_info.get("response") or response

        return (
            asset_id,
            status,
            self._response_json(final_response),
        )


class RH_SparkVideoAssetList(AssetRestNodeBase):
    ENDPOINT = "assets/list"
    RETURN_TYPES = ("STRING", "STRING", "STRING")
    RETURN_NAMES = ("items_json", "total_count", "response")

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "page_number": ("INT", {"default": 1, "min": 1, "max": 9999}),
                "page_size": ("INT", {"default": 20, "min": 1, "max": 100}),
            },
            "optional": {
                "group_id": connectable_string_input(),
                "status": text_input(),
                "name": text_input(),
                **cls.common_optional_inputs(),
            },
        }

    def build_payload(self, page_number, page_size, group_id="", status="", name="", **kwargs):
        payload = {
            "pageNumber": int(page_number),
            "pageSize": int(page_size),
        }

        group_id = clean_string(group_id)
        status = clean_string(status)
        name = clean_string(name)

        if group_id:
            payload["groupId"] = group_id
        if status:
            payload["status"] = status
        if name:
            payload["name"] = name

        return payload

    def parse_response(self, response, **kwargs):
        data = response.get("data") or {}
        items = data.get("items") or []
        return (
            dumps_json(items),
            clean_string(data.get("totalCount")),
            self._response_json(response),
        )


class RH_SparkVideoAssetQuery(AssetRestNodeBase):
    ENDPOINT = "assets/query"
    RETURN_TYPES = ("STRING", "STRING", "STRING", "STRING")
    RETURN_NAMES = ("asset_id", "status", "preview_url", "response")

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "asset_id": connectable_string_input(),
            },
            "optional": cls.common_optional_inputs(),
        }

    def build_payload(self, asset_id, **kwargs):
        return {"assetId": self._require_string("asset_id", asset_id)}

    def parse_response(self, response, **kwargs):
        data = response.get("data") or {}
        return (
            clean_string(data.get("assetId")),
            clean_string(data.get("status")),
            clean_string(data.get("previewUrl")),
            self._response_json(response),
        )


class RH_SparkVideoAssetIdsMerge:
    CATEGORY = "RunningHub/SparkVideo Assets"
    FUNCTION = "merge"
    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("asset_ids",)

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "asset_id1": connectable_string_input(),
            },
            "optional": {
                "asset_id2": connectable_string_input(),
                "asset_id3": connectable_string_input(),
                "asset_id4": connectable_string_input(),
                "asset_id5": connectable_string_input(),
                "asset_id6": connectable_string_input(),
                "asset_id7": connectable_string_input(),
                "asset_id8": connectable_string_input(),
                "asset_id9": connectable_string_input(),
                "asset_id10": connectable_string_input(),
            },
        }

    def merge(
        self,
        asset_id1,
        asset_id2="",
        asset_id3="",
        asset_id4="",
        asset_id5="",
        asset_id6="",
        asset_id7="",
        asset_id8="",
        asset_id9="",
        asset_id10="",
    ):
        asset_ids = _split_asset_ids(
            asset_id1,
            asset_id2,
            asset_id3,
            asset_id4,
            asset_id5,
            asset_id6,
            asset_id7,
            asset_id8,
            asset_id9,
            asset_id10,
        )
        if not asset_ids:
            raise ValueError("At least one asset_id is required")
        return (", ".join(asset_ids),)


class RH_SparkVideoAssetUpdate(AssetRestNodeBase):
    ENDPOINT = "assets/update"
    RETURN_TYPES = ("STRING", "STRING", "STRING", "STRING")
    RETURN_NAMES = ("asset_id", "name", "status", "response")

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "asset_id": connectable_string_input(),
                "name": text_input(),
            },
            "optional": cls.common_optional_inputs(),
        }

    def build_payload(self, asset_id, name, **kwargs):
        return {
            "assetId": self._require_string("asset_id", asset_id),
            "name": self._require_string("name", name),
        }

    def parse_response(self, response, **kwargs):
        data = response.get("data") or {}
        return (
            clean_string(data.get("assetId")),
            clean_string(data.get("name")),
            clean_string(data.get("status")),
            self._response_json(response),
        )


class RH_SparkVideoAssetDelete(AssetRestNodeBase):
    ENDPOINT = "assets/delete"
    RETURN_TYPES = ("STRING", "STRING", "STRING")
    RETURN_NAMES = ("asset_id", "status", "response")

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "asset_id": connectable_string_input(),
            },
            "optional": cls.common_optional_inputs(),
        }

    def build_payload(self, asset_id, **kwargs):
        return {"assetId": self._require_string("asset_id", asset_id)}

    def parse_response(self, response, asset_id="", **kwargs):
        return (
            clean_string(asset_id),
            "deleted",
            self._response_json(response),
        )
