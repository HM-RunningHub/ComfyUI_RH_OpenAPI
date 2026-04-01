"""
Dynamic node class generator for RunningHub OpenAPI models.

Creates ComfyUI node classes from model definitions in models_registry.json.

Media input handling:
  - IMAGE params become ComfyUI IMAGE inputs (tensor objects, not URLs)
  - VIDEO params become ComfyUI VIDEO inputs (VideoFromFile objects)
  - AUDIO params become ComfyUI AUDIO inputs (waveform dicts)
  - multipleInputs=True params are expanded: image1 (required) + image2..N (optional)
  - All media is uploaded to RH /media/upload/binary in prepare_inputs
  - build_payload uses the uploaded URLs
"""

import json
import os
import re
from typing import Dict, List, Any, Optional

from ..core.base import BaseNode
from ..core.api_key import get_config
from ..core.upload import upload_file
from ..core.image import tensor_to_bytes, download_images_to_tensor
from ..core.video import download_video
from ..core.audio import download_audio, audio_to_bytes
from ..core.rest import post_json
from .assets.asset_nodes import create_fixed_asset_from_media, preprocess_video_for_volc_asset


def _load_registry() -> List[Dict]:
    """Load model definitions from models_registry.json."""
    registry_path = os.path.join(
        os.path.dirname(os.path.dirname(__file__)), "models_registry.json"
    )
    with open(registry_path, "r", encoding="utf-8") as f:
        return json.load(f)


# ---------------------------------------------------------------------------
# Media field key -> ComfyUI-friendly input name conversion
# ---------------------------------------------------------------------------

def _field_key_to_comfy_name(field_key: str) -> str:
    """
    Convert API fieldKey to a user-friendly ComfyUI input name.

    Examples:
        imageUrl      -> image
        imageUrls     -> image
        firstImageUrl -> first_image
        lastImageUrl  -> last_image
        firstFrameUrl -> first_frame
        videoUrl      -> video
        videos        -> video
        audioUrl      -> audio
        cref          -> cref
        sref          -> sref
        leftImageUrl  -> left_image
    """
    name = field_key

    # Remove Url/Urls suffix
    if name.endswith("Urls"):
        name = name[:-4]
    elif name.endswith("Url"):
        name = name[:-3]

    # Handle 'videos' -> 'video'
    if name == "videos":
        name = "video"

    # Convert camelCase to snake_case
    name = re.sub(r"([A-Z])", r"_\1", name).lower().strip("_")

    return name


def _is_array_field(field_key: str) -> bool:
    """Check if the API field expects an array of URLs (plural key)."""
    return field_key.endswith("Urls") or field_key == "videos"


# ---------------------------------------------------------------------------
# INPUT_TYPES builder for non-media params
# ---------------------------------------------------------------------------

def _build_comfy_input_def(param: Dict) -> tuple:
    """Convert a single non-media param definition to ComfyUI INPUT_TYPES format."""
    ft = param.get("type", "STRING")
    fk = param.get("fieldKey", "")

    if ft == "LIST":
        options = [str(o["value"]) for o in param.get("options", [])]
        if not options:
            return ("STRING", {"default": ""})
        # Deduplicate options case-insensitively, keep first occurrence
        seen = set()
        unique_options = []
        for o in options:
            key = o.lower()
            if key not in seen:
                seen.add(key)
                unique_options.append(o)
        options = unique_options
        dv = param.get("defaultValue")
        if dv is not None:
            dv = str(dv)
            if dv not in options:
                dv = options[0]
        else:
            dv = options[0]
        return (options, {"default": dv})

    if ft == "STRING":
        is_prompt = fk.lower() in (
            "prompt", "text", "negativeprompt", "negative_prompt",
        )
        return ("STRING", {"multiline": is_prompt, "default": ""})

    if ft == "INT":
        opts = {}
        if param.get("min") is not None:
            opts["min"] = int(param["min"])
        if param.get("max") is not None:
            opts["max"] = int(param["max"])
        if param.get("step") is not None:
            opts["step"] = int(param["step"])
        dv = param.get("defaultValue")
        if dv is not None:
            try:
                opts["default"] = int(dv)
            except (ValueError, TypeError):
                pass
        return ("INT", opts)

    if ft == "FLOAT":
        opts = {}
        if param.get("min") is not None:
            opts["min"] = float(param["min"])
        if param.get("max") is not None:
            opts["max"] = float(param["max"])
        if param.get("step") is not None:
            opts["step"] = float(param["step"])
        dv = param.get("defaultValue")
        if dv is not None:
            try:
                opts["default"] = float(dv)
            except (ValueError, TypeError):
                pass
        return ("FLOAT", opts)

    if ft == "BOOLEAN":
        dv = param.get("defaultValue", False)
        if isinstance(dv, str):
            dv = dv.lower() in ("true", "1", "yes")
        return ("BOOLEAN", {"default": bool(dv)})

    # Fallback
    return ("STRING", {"default": ""})


def _build_asset_id_input_def() -> tuple:
    """Build a connectable STRING input for direct assetId references."""
    return ("STRING", {"default": "", "forceInput": True})


REAL_PERSON_ASSET_MODE_INPUT = "real_person_mode"
REAL_PERSON_TARGETS_INPUT = "conversion_slots"


def _build_real_person_mode_input_def() -> tuple:
    """Build the real person mode toggle input."""
    return (
        "BOOLEAN",
        {
            "default": False,
            "tooltip": (
                "When enabled, selected local IMAGE/VIDEO inputs are first converted "
                "to SparkVideo assets before the API request. If conversion fails for "
                "one slot, that slot falls back to the original upload path."
            ),
        },
    )


def _build_real_person_targets_input_def(allowed_slots: List[str]) -> tuple:
    """Build the slot selector input for real person mode."""
    slots = ", ".join(allowed_slots)
    return (
        "STRING",
        {
            "default": "all",
            "tooltip": (
                "Comma-separated slots to convert when real_person_mode is enabled. "
                "Use 'all' to convert every supported image/video slot. "
                f"Supported slots: {slots}"
            ),
        },
    )


def _parse_asset_ids(raw_value: Any) -> List[str]:
    """Parse asset_ids input from STRING/JSON array/comma/newline formats."""
    if raw_value is None:
        return []

    items: List[Any]
    if isinstance(raw_value, list):
        items = raw_value
    else:
        text = str(raw_value).strip()
        if not text:
            return []
        if text.startswith("["):
            try:
                parsed = json.loads(text)
                if isinstance(parsed, list):
                    items = parsed
                else:
                    items = [text]
            except Exception:
                items = re.split(r"[\n,]+", text)
        else:
            items = re.split(r"[\n,]+", text)

    result = []
    for item in items:
        if item is None:
            continue
        text = str(item).strip()
        if not text:
            continue
        if text.startswith("asset://"):
            text = text[8:]
        result.append(text)
    return result


def _asset_id_to_url(asset_id: str) -> str:
    """Normalize asset id to asset:// URL format."""
    asset_id = str(asset_id).strip()
    if not asset_id:
        return ""
    if asset_id.startswith("asset://"):
        return asset_id
    return f"asset://{asset_id}"


def _parse_real_person_targets(raw_value: Any, allowed_slots: List[str]) -> set:
    """Parse slot targets for selective media-to-asset conversion."""
    allowed = {str(slot).strip().lower() for slot in allowed_slots if str(slot).strip()}
    if not allowed:
        return set()

    text = str(raw_value or "").strip()
    if not text or text.lower() == "all":
        return set(allowed)

    result = set()
    for part in re.split(r"[\n,]+", text):
        slot = str(part).strip().lower()
        if not slot:
            continue
        if slot not in allowed:
            raise ValueError(
                f"Invalid {REAL_PERSON_TARGETS_INPUT}: {slot}. Allowed: {', '.join(sorted(allowed))}"
            )
        result.add(slot)
    return result


def _query_asset_type(
    asset_id: str,
    api_key: str,
    base_url: str,
    timeout: int,
    logger_prefix: str,
) -> str:
    """Query asset type for multimodal SparkVideo routing."""
    response = post_json(
        "assets/query",
        {"assetId": asset_id},
        api_key,
        base_url,
        timeout=timeout,
        logger_prefix=f"{logger_prefix}_AssetQuery",
    )
    data = response.get("data") or {}
    asset_type = str(data.get("assetType") or "").strip()
    if not asset_type:
        raise ValueError(f"assetId {asset_id} has no assetType")
    return asset_type


def _get_return_types(output_type: str):
    """Get RETURN_TYPES and RETURN_NAMES for output type.

    All nodes output: primary_result + url (STRING) + response (STRING)
    """
    mapping = {
        "image": (("IMAGE", "STRING", "STRING"), ("image", "url", "response")),
        "video": (("VIDEO", "STRING", "STRING"), ("video", "url", "response")),
        "audio": (("AUDIO", "STRING", "STRING"), ("audio", "url", "response")),
        "3d": (("STRING", "STRING", "STRING"), ("model_url", "url", "response")),
        "string": (("STRING", "STRING", "STRING"), ("result", "url", "response")),
    }
    return mapping.get(output_type, (("STRING", "STRING", "STRING"), ("result", "url", "response")))


# ---------------------------------------------------------------------------
# ComfyUI type mapping for media
# ---------------------------------------------------------------------------

_MEDIA_COMFY_TYPE = {
    "IMAGE": ("IMAGE",),
    "VIDEO": ("VIDEO",),
    "AUDIO": ("AUDIO",),
}

_DEFAULT_MULTI_COUNT = {"IMAGE": 9, "VIDEO": 3, "AUDIO": 3}


# ---------------------------------------------------------------------------
# Main factory
# ---------------------------------------------------------------------------

def create_node_class(model_def: Dict) -> type:
    """
    Create a ComfyUI node class from a model definition dict.

    Input ordering (top to bottom in ComfyUI UI):
      1. api_config (required, always first)
      2. Required media connectors (image, video, audio)
      3. Optional media connectors (image2..N, last_image, etc.)
      4. Required widget params (prompt, resolution, etc.)
      5. Optional widget params (aspectRatio, etc.)

    Media handling:
      - Single media params (multipleInputs=False):
          ComfyUI input named e.g. 'image', 'first_image', 'video', 'audio'
      - Multiple media params (multipleInputs=True, maxInputNum=N):
          ComfyUI inputs: image1 (required), image2..imageN (optional)
      - All media is uploaded in prepare_inputs, URLs used in build_payload
    """
    endpoint = model_def["endpoint"]
    model_params = model_def["params"]
    output_type = model_def.get("output_type", "image")
    category = model_def.get("category", "RunningHub")
    class_name = model_def.get("class_name", "GeneratedNode")
    asset_ids_mode = model_def.get("asset_ids_mode", "")
    real_person_asset_slots = [
        str(slot).strip()
        for slot in model_def.get("real_person_asset_slots", [])
        if str(slot).strip()
    ]

    # ---- Separate media vs non-media params ----
    media_params = [p for p in model_params if p["type"] in ("IMAGE", "VIDEO", "AUDIO")]
    non_media_params = [p for p in model_params if p["type"] not in ("IMAGE", "VIDEO", "AUDIO")]

    # Sort non-media: prompt/text fields first, then negative_prompt, then others
    _PROMPT_KEYS = {"prompt", "text"}
    _NEG_PROMPT_KEYS = {"negativeprompt", "negative_prompt"}

    def _param_sort_key(p):
        fk_lower = p["fieldKey"].lower()
        if fk_lower in _PROMPT_KEYS:
            return (0, fk_lower)
        if fk_lower in _NEG_PROMPT_KEYS:
            return (1, fk_lower)
        return (2, "")

    non_media_params = sorted(non_media_params, key=_param_sort_key)

    # ---- Build INPUT_TYPES with controlled ordering ----
    required_inputs = {}
    optional_inputs = {}

    # Collect non-media params into required/optional buckets
    req_non_media = {}
    opt_non_media = {}
    for p in non_media_params:
        fk = p["fieldKey"]
        comfy_def = _build_comfy_input_def(p)
        if p.get("required", False):
            req_non_media[fk] = comfy_def
        else:
            opt_non_media[fk] = comfy_def

    def _field_supports_asset_ids(field_key: str) -> bool:
        if asset_ids_mode == "image_to_video":
            return field_key in ("firstFrameUrl", "lastFrameUrl")
        if asset_ids_mode == "multimodal_video":
            return field_key in ("imageUrls", "videoUrls", "audioUrls")
        return False

    # Collect media params and build media_info list
    req_media = {}
    opt_media = {}
    media_info_list = []

    for p in media_params:
        field_key = p["fieldKey"]
        media_type = p["type"]
        is_required = p.get("required", False)
        is_multiple = p.get("multipleInputs", False)
        max_num = p.get("maxInputNum") or 0
        if is_multiple and max_num <= 1:
            max_num = _DEFAULT_MULTI_COUNT.get(media_type, 5)
        elif max_num <= 0:
            max_num = 1
        base_name = _field_key_to_comfy_name(field_key)
        is_array = _is_array_field(field_key) or (is_multiple and max_num > 1)
        comfy_type = _MEDIA_COMFY_TYPE.get(media_type, ("IMAGE",))
        effective_required = is_required and not _field_supports_asset_ids(field_key)

        if is_multiple and max_num > 1:
            # Expand: image1 (required) + image2..imageN (optional)
            for i in range(1, max_num + 1):
                comfy_name = f"{base_name}{i}"
                if i == 1 and effective_required:
                    req_media[comfy_name] = comfy_type
                else:
                    opt_media[comfy_name] = comfy_type
                media_info_list.append({
                    "comfy_name": comfy_name,
                    "field_key": field_key,
                    "media_type": media_type,
                    "is_array_in_payload": True,
                })
        else:
            # Single input
            comfy_name = base_name
            # Avoid name collisions with non-media params
            all_existing = {**required_inputs, **req_non_media, **opt_non_media, **req_media, **opt_media}
            if comfy_name in all_existing:
                comfy_name = f"{base_name}_input"
            if effective_required:
                req_media[comfy_name] = comfy_type
            else:
                opt_media[comfy_name] = comfy_type
            media_info_list.append({
                "comfy_name": comfy_name,
                "field_key": field_key,
                "media_type": media_type,
                "is_array_in_payload": is_array,
            })

    # ---- Assemble final dicts with controlled order ----
    # Required order: api_config -> media connectors -> widget params
    required_inputs.update(req_media)
    required_inputs.update(req_non_media)

    # Optional order: media connectors -> widget params -> api_config -> skip_error
    optional_inputs.update(opt_media)
    optional_inputs.update(opt_non_media)
    if asset_ids_mode:
        optional_inputs["asset_ids"] = _build_asset_id_input_def()
    optional_inputs["api_config"] = ("RH_OPENAPI_CONFIG",)
    optional_inputs["skip_error"] = ("BOOLEAN", {"default": False})
    optional_inputs["seed"] = ("INT", {"default": 0, "min": 0, "max": 0xFFFFFFFFFFFFFFFF})
    if real_person_asset_slots:
        optional_inputs[REAL_PERSON_ASSET_MODE_INPUT] = _build_real_person_mode_input_def()
        optional_inputs[REAL_PERSON_TARGETS_INPUT] = _build_real_person_targets_input_def(
            real_person_asset_slots
        )

    ret_types, ret_names = _get_return_types(output_type)

    # ---- Freeze all values for closure safety ----
    _endpoint = endpoint
    _category = category
    _output_type = output_type
    _ret_types = ret_types
    _ret_names = ret_names
    _required = dict(required_inputs)
    _optional = dict(optional_inputs)
    _media_info = list(media_info_list)
    _non_media = list(non_media_params)
    _asset_ids_mode = asset_ids_mode
    _real_person_slots = list(real_person_asset_slots)

    class NodeClass(BaseNode):
        ENDPOINT = _endpoint
        CATEGORY = _category
        OUTPUT_TYPE = _output_type
        RETURN_TYPES = _ret_types
        RETURN_NAMES = _ret_names
        FUNCTION = "execute"

        @classmethod
        def INPUT_TYPES(cls):
            return {"required": _required, "optional": _optional}

        def prepare_inputs(self, **kwargs):
            """Upload local media and resolve unified asset_ids when enabled."""
            uploaded = {}
            if not _media_info and not _asset_ids_mode:
                return uploaded

            config = get_config(kwargs.get("api_config"))
            base_url = config["base_url"]
            api_key = config["api_key"]
            timeout = config.get("timeout", 60)
            provided_by_field = {}
            real_person_mode = bool(kwargs.get(REAL_PERSON_ASSET_MODE_INPUT, False))
            target_slots = set()
            if real_person_mode and _real_person_slots:
                target_slots = _parse_real_person_targets(
                    kwargs.get(REAL_PERSON_TARGETS_INPUT, "all"),
                    _real_person_slots,
                )

            for mi in _media_info:
                value = kwargs.get(mi["comfy_name"])
                if value is None:
                    continue

                if (
                    real_person_mode
                    and mi["comfy_name"] in target_slots
                    and mi["media_type"] in ("IMAGE", "VIDEO")
                ):
                    try:
                        asset_info = create_fixed_asset_from_media(
                            config,
                            mi["media_type"],
                            value,
                            f"{self._log_prefix}_{mi['comfy_name']}",
                        )
                        uploaded[f"__url_{mi['comfy_name']}"] = asset_info["asset_url"]
                        provided_by_field[mi["field_key"]] = provided_by_field.get(mi["field_key"], 0) + 1
                        continue
                    except Exception as e:
                        print(
                            f"[{self._log_prefix}] WARNING: asset conversion failed for "
                            f"{mi['comfy_name']}, fallback to standard upload path: {e}"
                        )

                mt = mi["media_type"]
                url = None

                if mt == "IMAGE":
                    img_bytes = tensor_to_bytes(value)
                    fn = f"upload_{hash(img_bytes) % 10**10}.png"
                    url = upload_file(
                        img_bytes, fn, "image/png",
                        config["api_key"], config["base_url"],
                        timeout=config.get("upload_timeout", 60),
                        logger_prefix=self._log_prefix,
                    )

                elif mt == "VIDEO":
                    vbytes = None
                    upload_filename = None
                    upload_mime_type = "video/mp4"
                    should_normalize_video_upload = (
                        mi["field_key"] == "videoUrls" and _asset_ids_mode == "multimodal_video"
                    )

                    if should_normalize_video_upload:
                        try:
                            prepared_video = preprocess_video_for_volc_asset(
                                value,
                                f"{self._log_prefix}_{mi['comfy_name']}_DirectUpload",
                            )
                            vbytes = prepared_video.get("file_bytes")
                            upload_filename = prepared_video.get("filename")
                            upload_mime_type = prepared_video.get("mime_type") or "video/mp4"
                        except Exception as e:
                            print(
                                f"[{self._log_prefix}] WARNING: video preprocessing failed for "
                                f"{mi['comfy_name']}, fallback to original upload: {e}"
                            )

                    if not vbytes:
                        if hasattr(value, "get_stream_source"):
                            source = value.get_stream_source()
                            if isinstance(source, str):
                                with open(source, "rb") as f:
                                    vbytes = f.read()
                            elif hasattr(source, "read"):
                                vbytes = source.read()
                        elif hasattr(value, "path"):
                            with open(value.path, "rb") as f:
                                vbytes = f.read()
                        elif hasattr(value, "file_path"):
                            with open(value.file_path, "rb") as f:
                                vbytes = f.read()
                        elif isinstance(value, dict):
                            p = value.get("file_path") or value.get("path")
                            if p and os.path.isfile(p):
                                with open(p, "rb") as f:
                                    vbytes = f.read()
                        elif isinstance(value, str) and os.path.isfile(value):
                            with open(value, "rb") as f:
                                vbytes = f.read()

                    if vbytes:
                        fn = upload_filename or f"upload_{hash(vbytes) % 10**10}.mp4"
                        url = upload_file(
                            vbytes, fn, upload_mime_type,
                            config["api_key"], config["base_url"],
                            timeout=config.get("upload_timeout", 120),
                            logger_prefix=self._log_prefix,
                        )
                    else:
                        print(f"[{self._log_prefix}] WARNING: Could not extract video data from {type(value).__name__}")

                elif mt == "AUDIO":
                    if isinstance(value, dict) and "waveform" in value:
                        abytes = audio_to_bytes(value)
                        fn = f"upload_{hash(abytes) % 10**10}.wav"
                        url = upload_file(
                            abytes, fn, "audio/wav",
                            config["api_key"], config["base_url"],
                            timeout=config.get("upload_timeout", 60),
                            logger_prefix=self._log_prefix,
                        )

                if url:
                    uploaded[f"__url_{mi['comfy_name']}"] = url
                    provided_by_field[mi["field_key"]] = provided_by_field.get(mi["field_key"], 0) + 1

            asset_ids = _parse_asset_ids(kwargs.get("asset_ids")) if _asset_ids_mode else []
            asset_field_values = {}

            if asset_ids:
                asset_urls = [_asset_id_to_url(asset_id) for asset_id in asset_ids]

                if _asset_ids_mode == "image_to_video":
                    if len(asset_urls) > 2:
                        raise ValueError("asset_ids supports at most 2 entries for SparkVideo image-to-video")

                    if asset_urls:
                        if provided_by_field.get("firstFrameUrl", 0) > 0:
                            raise ValueError("asset_ids conflicts with first_frame; provide one source only")
                        asset_field_values["firstFrameUrl"] = asset_urls[0]
                        provided_by_field["firstFrameUrl"] = provided_by_field.get("firstFrameUrl", 0) + 1

                    if len(asset_urls) > 1:
                        if provided_by_field.get("lastFrameUrl", 0) > 0:
                            raise ValueError("The second asset_id conflicts with last_frame; provide one source only")
                        asset_field_values["lastFrameUrl"] = asset_urls[1]
                        provided_by_field["lastFrameUrl"] = provided_by_field.get("lastFrameUrl", 0) + 1

                elif _asset_ids_mode == "multimodal_video":
                    type_to_field = {
                        "image": "imageUrls",
                        "video": "videoUrls",
                        "audio": "audioUrls",
                    }
                    for asset_id, asset_url in zip(asset_ids, asset_urls):
                        asset_type = _query_asset_type(
                            asset_id,
                            api_key,
                            base_url,
                            timeout,
                            self._log_prefix,
                        ).lower()
                        field_key = type_to_field.get(asset_type)
                        if not field_key:
                            raise ValueError(
                                f"Unsupported assetType for asset_id {asset_id}: {asset_type or 'unknown'}"
                            )
                        asset_field_values.setdefault(field_key, []).append(asset_url)
                        provided_by_field[field_key] = provided_by_field.get(field_key, 0) + 1

            if _asset_ids_mode == "image_to_video" and provided_by_field.get("firstFrameUrl", 0) <= 0:
                raise ValueError("Provide first_frame or asset_ids")

            if asset_field_values:
                uploaded["__asset_field_values"] = asset_field_values

            return uploaded

        def build_payload(self, **kwargs):
            """Build API request payload."""
            payload = {}

            # Non-media params
            for p in _non_media:
                fk = p["fieldKey"]
                ft = p["type"]
                val = kwargs.get(fk)
                if val is not None:
                    if ft == "INT":
                        payload[fk] = int(val)
                    elif ft == "FLOAT":
                        payload[fk] = float(val)
                    elif ft == "BOOLEAN":
                        payload[fk] = bool(val)
                    elif ft == "STRING":
                        s = str(val).strip()
                        if s:
                            payload[fk] = s
                    else:
                        # LIST and others
                        payload[fk] = str(val)

            # Media params - group array fields
            array_urls = {}  # field_key -> [url1, url2, ...]

            for mi in _media_info:
                url = kwargs.get(f"__url_{mi['comfy_name']}")
                if url is None:
                    continue

                if mi["is_array_in_payload"]:
                    array_urls.setdefault(mi["field_key"], []).append(url)
                else:
                    payload[mi["field_key"]] = url

            # Add array fields to payload
            for field_key, urls in array_urls.items():
                payload[field_key] = urls

            # Merge asset:// URLs resolved from unified asset_ids input
            asset_field_values = kwargs.get("__asset_field_values") or {}
            for field_key, value in asset_field_values.items():
                if isinstance(value, list):
                    if not value:
                        continue
                    if field_key in payload and isinstance(payload[field_key], list):
                        payload[field_key] = payload[field_key] + value
                    elif field_key in payload and payload[field_key]:
                        payload[field_key] = [payload[field_key]] + value
                    else:
                        payload[field_key] = list(value)
                else:
                    if field_key in payload and payload[field_key]:
                        raise ValueError(f"Both local media and asset_ids attempted to fill {field_key}")
                    payload[field_key] = value

            return payload

        def process_result(self, result_urls):
            """Download and convert results based on output type."""
            if not result_urls:
                raise RuntimeError("No result URLs returned from API")

            if _output_type == "image":
                batch = download_images_to_tensor(
                    result_urls[:5], logger_prefix=self._log_prefix
                )
                return (batch,)
            elif _output_type == "video":
                video = download_video(
                    result_urls[0], logger_prefix=self._log_prefix
                )
                return (video,)
            elif _output_type == "audio":
                audio_result = download_audio(
                    result_urls[0], logger_prefix=self._log_prefix
                )
                return (audio_result,)
            elif _output_type == "3d":
                return (result_urls[0],)
            else:
                return (result_urls[0],)

    # Set proper class identity
    NodeClass.__name__ = class_name
    NodeClass.__qualname__ = class_name

    return NodeClass


def create_all_nodes():
    """
    Create all node classes from the model registry.

    Returns:
        (NODE_CLASS_MAPPINGS, NODE_DISPLAY_NAME_MAPPINGS) tuple
    """
    registry = _load_registry()

    class_mappings = {}
    display_mappings = {}

    for model_def in registry:
        try:
            internal_name = model_def["internal_name"]
            display_name = model_def["display_name"]

            node_class = create_node_class(model_def)
            class_mappings[internal_name] = node_class
            display_mappings[internal_name] = display_name
        except Exception as e:
            print(
                f"[RH_OpenAPI] WARNING: Failed to create node for "
                f"{model_def.get('endpoint', '?')}: {e}"
            )

    print(f"[RH_OpenAPI] Registered {len(class_mappings)} API nodes")
    return class_mappings, display_mappings
