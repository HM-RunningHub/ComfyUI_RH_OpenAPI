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

    # ---- Separate media vs non-media params ----
    media_params = [p for p in model_params if p["type"] in ("IMAGE", "VIDEO", "AUDIO")]
    non_media_params = [p for p in model_params if p["type"] not in ("IMAGE", "VIDEO", "AUDIO")]

    # ---- Build INPUT_TYPES with controlled ordering ----
    # api_config is always first required input so it shows at the top
    required_inputs = {"api_config": ("RH_OPENAPI_CONFIG",)}
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

    # Collect media params and build media_info list
    req_media = {}
    opt_media = {}
    media_info_list = []

    for p in media_params:
        field_key = p["fieldKey"]
        media_type = p["type"]
        is_required = p.get("required", False)
        is_multiple = p.get("multipleInputs", False)
        max_num = p.get("maxInputNum", 1) or 1
        base_name = _field_key_to_comfy_name(field_key)
        is_array = _is_array_field(field_key) or (is_multiple and max_num > 1)
        comfy_type = _MEDIA_COMFY_TYPE.get(media_type, ("IMAGE",))

        if is_multiple and max_num > 1:
            # Expand: image1 (required) + image2..imageN (optional)
            for i in range(1, max_num + 1):
                comfy_name = f"{base_name}{i}"
                if i == 1 and is_required:
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
            if is_required:
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

    # Optional order: media connectors -> widget params
    optional_inputs.update(opt_media)
    optional_inputs.update(opt_non_media)

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
            """Upload all IMAGE/VIDEO/AUDIO inputs and return their URLs."""
            uploaded = {}
            if not _media_info:
                return uploaded

            config = get_config(kwargs.get("api_config"))

            for mi in _media_info:
                value = kwargs.get(mi["comfy_name"])
                if value is None:
                    continue

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
                    video_path = None
                    if hasattr(value, "path"):
                        video_path = value.path
                    elif hasattr(value, "file_path"):
                        video_path = value.file_path
                    elif isinstance(value, str) and os.path.isfile(value):
                        video_path = value

                    if video_path:
                        with open(video_path, "rb") as f:
                            vbytes = f.read()
                        fn = f"upload_{hash(vbytes) % 10**10}.mp4"
                        url = upload_file(
                            vbytes, fn, "video/mp4",
                            config["api_key"], config["base_url"],
                            timeout=config.get("upload_timeout", 120),
                            logger_prefix=self._log_prefix,
                        )

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
