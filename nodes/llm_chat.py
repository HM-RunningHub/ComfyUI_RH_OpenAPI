"""RunningHub LLM chat completions node."""

from __future__ import annotations

import base64
import json
import os
import re
import shutil
import subprocess
import tempfile
import time
from io import BytesIO
from typing import Any, Dict, Iterable, List, Optional

import requests

from ..core.api_key import get_config
from ..core.image import tensor_to_pil
from ..core.upload import upload_file


LLM_BASE_URL = "https://llm.runninghub.cn/v1"
LLM_MODELS_URL = "https://llm.runninghub.ai/v1/models"
LLM_CHAT_URL = f"{LLM_BASE_URL}/chat/completions"
MAX_VIDEO_BYTES = 10 * 1024 * 1024
MAX_VIDEO_DURATION = 15
MODEL_CACHE_TTL_SECONDS = 3600
CHAT_MAX_RETRIES = 3
DEFAULT_MAX_TOKENS = 4096

_MODEL_CACHE: Dict[str, Any] = {"expires_at": 0.0, "models": None}

FALLBACK_MODELS = [
    "qwen/qwen3-vl-235b-a22b-instruct",
    "qwen/qwen-plus",
    "qwen/qwen-max",
    "qwen/qwen3-235b-a22b-2507",
    "deepseek/deepseek-v3.2",
    "deepseek/deepseek-chat",
    "rh-llm-o/rh-t-55",
    "rh-llm-o/rh-t-54",
    "rh-llm-g/rh-g-flash-preview-3",
    "rh-llm-g/rh-g-pro-preview-31",
]


def remove_think_tags(text: Any) -> Any:
    """Remove common hidden reasoning tags from model responses."""
    if not isinstance(text, str) or not text:
        return text
    cleaned = re.sub(r"<think>.*?</think>", "", text, flags=re.IGNORECASE | re.DOTALL)
    cleaned = re.sub(r"</?think>", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"<\|begin_of_box\|>|<\|end_of_box\|>", "", cleaned)
    return cleaned.strip()


def fetch_llm_models(force: bool = False) -> List[str]:
    """Fetch model ids from RunningHub LLM API with a one-hour cache."""
    now = time.time()
    cached = _MODEL_CACHE.get("models")
    if not force and cached and now < float(_MODEL_CACHE.get("expires_at", 0)):
        return list(cached)

    try:
        response = requests.get(LLM_MODELS_URL, timeout=5)
        response.raise_for_status()
        data = response.json()
        models = [
            str(item.get("id")).strip()
            for item in data.get("data", [])
            if isinstance(item, dict) and str(item.get("id", "")).strip()
        ]
        if models:
            _MODEL_CACHE["models"] = models
            _MODEL_CACHE["expires_at"] = now + MODEL_CACHE_TTL_SECONDS
            return models
    except Exception as exc:
        print(f"[RH_LLMChat] Failed to fetch model list, using fallback: {type(exc).__name__}")

    return list(FALLBACK_MODELS)


def _image_to_jpeg_bytes(images: Iterable[Any]) -> List[bytes]:
    image_bytes: List[bytes] = []
    for image in images:
        for pil_image in tensor_to_pil(image):
            if pil_image.mode != "RGB":
                pil_image = pil_image.convert("RGB")
            buffer = BytesIO()
            pil_image.save(buffer, format="JPEG", quality=90)
            image_bytes.append(buffer.getvalue())
    return image_bytes


def upload_images(images: Iterable[Any], config: Dict[str, Any]) -> List[str]:
    """Upload ComfyUI IMAGE inputs and return public URLs for LLM vision payloads."""
    urls: List[str] = []
    for index, jpeg_bytes in enumerate(_image_to_jpeg_bytes(images), start=1):
        url = upload_file(
            jpeg_bytes,
            f"rh_llm_image_{index}.jpg",
            "image/jpeg",
            config["api_key"],
            config["base_url"],
            timeout=config.get("upload_timeout", 60),
            logger_prefix=f"RH_LLMChat_Image{index}",
        )
        urls.append(url)
    return urls


def _copy_file_like_to_temp(file_obj: Any) -> Optional[str]:
    if not hasattr(file_obj, "read"):
        return None
    try:
        if hasattr(file_obj, "seek"):
            file_obj.seek(0)
        handle = tempfile.NamedTemporaryFile(delete=False, suffix=".mp4")
        with handle:
            handle.write(file_obj.read())
        return handle.name
    except Exception:
        return None


def _extract_video_path(video: Any) -> Optional[str]:
    if isinstance(video, str) and os.path.exists(video):
        return video
    if isinstance(video, dict):
        for key in ("file_path", "path", "filename"):
            value = video.get(key)
            if isinstance(value, str) and os.path.exists(value):
                return value

    file_obj = getattr(video, "_VideoFromFile__file", None)
    if isinstance(file_obj, str) and os.path.exists(file_obj):
        return file_obj
    copied = _copy_file_like_to_temp(file_obj)
    if copied:
        return copied

    for attr in ("path", "file"):
        value = getattr(video, attr, None)
        if isinstance(value, str) and os.path.exists(value):
            return value

    if hasattr(video, "get_stream_source"):
        try:
            value = video.get_stream_source()
            if isinstance(value, str) and os.path.exists(value):
                return value
        except Exception:
            pass

    if hasattr(video, "save_to"):
        try:
            handle = tempfile.NamedTemporaryFile(delete=False, suffix=".mp4")
            handle.close()
            video.save_to(handle.name)
            if os.path.exists(handle.name):
                return handle.name
        except Exception:
            pass

    return None


def _compress_video(input_path: str) -> Optional[str]:
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        return None

    output_path = os.path.join(
        tempfile.gettempdir(),
        f"rh_llm_video_{int(time.time() * 1000)}.mp4",
    )
    command = [
        ffmpeg,
        "-y",
        "-i",
        input_path,
        "-t",
        str(MAX_VIDEO_DURATION),
        "-fs",
        str(MAX_VIDEO_BYTES),
        "-vcodec",
        "libx264",
        "-preset",
        "veryfast",
        "-crf",
        "28",
        "-acodec",
        "aac",
        output_path,
    ]
    try:
        subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
    except Exception as exc:
        print(f"[RH_LLMChat] ffmpeg compression failed: {type(exc).__name__}")
        return None

    if os.path.exists(output_path) and os.path.getsize(output_path) <= MAX_VIDEO_BYTES:
        return output_path
    return None


def _encode_video(video: Any) -> str:
    path = _extract_video_path(video)
    if not path:
        raise RuntimeError("Unable to resolve video file path from VIDEO input.")

    cleanup_paths = []
    if path.startswith(tempfile.gettempdir()):
        cleanup_paths.append(path)

    try:
        use_path = path
        if os.path.getsize(use_path) > MAX_VIDEO_BYTES:
            compressed = _compress_video(use_path)
            if not compressed:
                raise RuntimeError("Video exceeds 10MB and ffmpeg compression is unavailable or failed.")
            cleanup_paths.append(compressed)
            use_path = compressed

        if os.path.getsize(use_path) > MAX_VIDEO_BYTES:
            raise RuntimeError("Video is still larger than 10MB after processing.")

        with open(use_path, "rb") as handle:
            return base64.b64encode(handle.read()).decode("utf-8")
    finally:
        for cleanup_path in cleanup_paths:
            try:
                os.remove(cleanup_path)
            except Exception:
                pass


def build_messages(
    role: str,
    prompt: str,
    image_urls: Optional[List[str]] = None,
    video: Any = None,
) -> List[Dict[str, Any]]:
    """Build OpenAI-compatible chat messages."""
    if image_urls:
        content = [{"type": "text", "text": prompt or ""}]
        for url in image_urls:
            content.append({
                "type": "image_url",
                "image_url": {"url": url},
            })
        return [
            {"role": "system", "content": role or ""},
            {"role": "user", "content": content},
        ]

    if video is not None:
        encoded_video = _encode_video(video)
        return [
            {"role": "system", "content": role or ""},
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt or ""},
                    {
                        "type": "video_url",
                        "video_url": {"url": f"data:video/mp4;base64,{encoded_video}"},
                    },
                ],
            },
        ]

    return [
        {"role": "system", "content": role or ""},
        {"role": "user", "content": prompt or ""},
    ]


def build_chat_payload(
    model: str,
    messages: List[Dict[str, Any]],
    temperature: float,
    max_tokens: int,
    top_p: float,
    presence_penalty: float,
    frequency_penalty: float,
    reasoning_effort: str,
    seed: int,
) -> Dict[str, Any]:
    # The RunningHub LLM gateway currently rejects seed for some providers
    # (for example Claude vision) with an internal_error, so keep the ComfyUI
    # widget for workflow compatibility but do not forward it to the API.
    payload: Dict[str, Any] = {
        "model": model,
        "messages": messages,
        "max_tokens": int(max_tokens),
        "temperature": float(temperature),
        "top_p": float(top_p),
        "presence_penalty": float(presence_penalty),
        "frequency_penalty": float(frequency_penalty),
        "reasoning_effort": reasoning_effort or "none",
    }
    return payload


def _redact_payload_for_log(value: Any) -> Any:
    if isinstance(value, dict):
        redacted = {}
        for key, item in value.items():
            if key in {"image_url", "video_url"} and isinstance(item, dict):
                url = str(item.get("url", ""))
                if url.startswith("data:"):
                    redacted[key] = {"url": f"{url[:32]}...<base64 {len(url)} chars>"}
                else:
                    redacted[key] = item
            else:
                redacted[key] = _redact_payload_for_log(item)
        return redacted
    if isinstance(value, list):
        return [_redact_payload_for_log(item) for item in value]
    return value


def post_chat_completion(headers: Dict[str, str], payload: Dict[str, Any], timeout: int) -> Dict[str, Any]:
    """POST chat completion with short retries for transient upstream errors."""
    last_error: Optional[RuntimeError] = None
    for attempt in range(CHAT_MAX_RETRIES):
        if attempt > 0:
            wait = min(2 ** attempt, 5)
            print(f"[RH_LLMChat] Chat retry {attempt + 1}/{CHAT_MAX_RETRIES} in {wait}s...")
            time.sleep(wait)

        if attempt == 0:
            print(f"[RH_LLMChat] POST {LLM_CHAT_URL}")
            print(
                "[RH_LLMChat] Payload: "
                + json.dumps(_redact_payload_for_log(payload), ensure_ascii=False, indent=2)
            )
        response = requests.post(LLM_CHAT_URL, headers=headers, json=payload, timeout=timeout)
        try:
            data = response.json()
        except ValueError as exc:
            raise RuntimeError(f"Invalid JSON response: {response.text[:200]}") from exc

        if response.status_code == 200:
            return data

        message = data.get("error") or data.get("message") or data.get("msg") or response.text[:200]
        last_error = RuntimeError(f"HTTP {response.status_code}: {message}")
        if response.status_code >= 500 or response.status_code == 429:
            print(f"[RH_LLMChat] Attempt {attempt + 1} failed: {last_error}")
            continue
        raise last_error

    raise last_error or RuntimeError("LLM chat request failed")


def _calculate_timeout(role: str, prompt: str, image_count: int, has_video: bool) -> int:
    total_length = len(role or "") + len(prompt or "")
    if total_length <= 300:
        timeout = 90
    elif total_length <= 2000:
        timeout = 120
    elif total_length <= 5000:
        timeout = 150
    elif total_length <= 10000:
        timeout = 180
    else:
        timeout = 210
    timeout += min(image_count, 8) * 30
    if has_video:
        timeout += 120
    return min(timeout, 360)


class RHLLMChatNode:
    """RunningHub LLM Chat Completions."""

    RETURN_TYPES = ("STRING", "STRING")
    RETURN_NAMES = ("response", "raw_response")
    FUNCTION = "chat"
    CATEGORY = "RunningHub/LLM"
    OUTPUT_NODE = True
    API_NODE = True

    @classmethod
    def INPUT_TYPES(cls):
        models = fetch_llm_models()
        return {
            "required": {
                "model": (models, {"default": models[0]}),
                "role": ("STRING", {"multiline": True, "default": "You are a helpful assistant"}),
                "prompt": ("STRING", {"multiline": True, "default": "Hello"}),
                "temperature": ("FLOAT", {"default": 0.6, "min": 0.0, "max": 2.0, "step": 0.1}),
                "max_tokens": ("INT", {"default": DEFAULT_MAX_TOKENS, "min": 1, "max": 32768, "step": 1}),
                "top_p": ("FLOAT", {"default": 1.0, "min": 0.0, "max": 1.0, "step": 0.01}),
                "presence_penalty": ("FLOAT", {"default": 0.0, "min": -2.0, "max": 2.0, "step": 0.1}),
                "frequency_penalty": ("FLOAT", {"default": 0.0, "min": -2.0, "max": 2.0, "step": 0.1}),
                "reasoning_effort": (["none", "low", "medium", "high"], {"default": "none"}),
                "seed": ("INT", {"default": -1, "min": -1, "max": 2147483647, "step": 1}),
            },
            "optional": {
                "skip_error": ("BOOLEAN", {"default": False}),
                "image1": ("IMAGE",),
                "image2": ("IMAGE",),
                "image3": ("IMAGE",),
                "image4": ("IMAGE",),
                "image5": ("IMAGE",),
                "image6": ("IMAGE",),
                "image7": ("IMAGE",),
                "image8": ("IMAGE",),
                "video": ("VIDEO",),
                "api_config": ("RH_OPENAPI_CONFIG",),
            },
        }

    def _make_error_result(self, error: Exception) -> Dict[str, Any]:
        message = f"[ERROR] RH_LLMChat: {error}"
        raw = json.dumps({"error": str(error)}, ensure_ascii=False, indent=2)
        return {"ui": {"text": [message, raw]}, "result": (message, raw)}

    def chat(
        self,
        model,
        role,
        prompt,
        temperature,
        max_tokens,
        top_p,
        presence_penalty,
        frequency_penalty,
        reasoning_effort,
        seed,
        api_config=None,
        skip_error=False,
        image1=None,
        image2=None,
        image3=None,
        image4=None,
        image5=None,
        image6=None,
        image7=None,
        image8=None,
        video=None,
    ):
        try:
            return self._chat_inner(
                model=model,
                role=role,
                prompt=prompt,
                temperature=temperature,
                max_tokens=max_tokens,
                top_p=top_p,
                presence_penalty=presence_penalty,
                frequency_penalty=frequency_penalty,
                reasoning_effort=reasoning_effort,
                seed=seed,
                api_config=api_config,
                images=[img for img in (image1, image2, image3, image4, image5, image6, image7, image8) if img is not None],
                video=video,
            )
        except Exception as exc:
            if skip_error:
                print(f"[RH_LLMChat] skip_error=True, returning error text: {exc}")
                return self._make_error_result(exc)
            raise

    def _chat_inner(
        self,
        model,
        role,
        prompt,
        temperature,
        max_tokens,
        top_p,
        presence_penalty,
        frequency_penalty,
        reasoning_effort,
        seed,
        api_config,
        images,
        video,
    ):
        config = get_config(api_config)
        api_key = config["api_key"]
        timeout = _calculate_timeout(role, prompt, len(images), video is not None and not images)

        if images and video is not None:
            print("[RH_LLMChat] Both images and video provided; using images and ignoring video.")

        image_urls = upload_images(images, config) if images else []
        messages = build_messages(role, prompt, image_urls, video if not image_urls else None)
        payload = build_chat_payload(
            model,
            messages,
            temperature,
            max_tokens,
            top_p,
            presence_penalty,
            frequency_penalty,
            reasoning_effort,
            seed,
        )
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }

        data = post_chat_completion(headers, payload, timeout)

        choices = data.get("choices")
        if not choices or not isinstance(choices, list):
            raise RuntimeError("LLM API returned no choices.")

        first = choices[0] if isinstance(choices[0], dict) else {}
        message = first.get("message") if isinstance(first.get("message"), dict) else {}
        content = message.get("content")
        if isinstance(content, list):
            content = "\n".join(
                str(item.get("text", ""))
                for item in content
                if isinstance(item, dict) and item.get("text")
            )
        if content is None:
            content = first.get("text")
        if not content:
            raise RuntimeError("LLM API returned empty content.")

        cleaned = remove_think_tags(str(content))
        raw = json.dumps(data, ensure_ascii=False, indent=2)
        return {"ui": {"text": [cleaned, raw]}, "result": (cleaned, raw)}
