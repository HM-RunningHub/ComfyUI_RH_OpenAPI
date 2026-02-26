"""
Base classes for API nodes.

Unified flow: prepare_inputs -> build_payload -> submit -> poll -> process_result

All nodes output 3 groups:
  1. Primary result (IMAGE/VIDEO/AUDIO/STRING based on output_type)
  2. url: raw result URL(s) from RH API
  3. response: full JSON response from RH API
"""

import time
import json
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

from .api_key import get_config
from .upload import upload_file
from .task import submit, poll
from .image import tensor_to_bytes, download_images_to_tensor
from .video import download_video
from .audio import download_audio

# ComfyUI dependency
try:
    import comfy.utils
    COMFYUI_AVAILABLE = True
except ImportError:
    COMFYUI_AVAILABLE = False
    class ProgressBar:
        def __init__(self, *args, **kwargs): pass
        def update_absolute(self, *args, **kwargs): pass
    comfy = type("comfy", (), {"utils": type("utils", (), {"ProgressBar": ProgressBar})()})


class BaseNode(ABC):
    """Base node for RH OpenAPI."""

    ENDPOINT: str = ""
    OUTPUT_TYPE: str = "image"  # "image" | "video" | "audio" | "3d" | "string"
    CATEGORY: str = "RunningHub"
    FUNCTION: str = "execute"
    OUTPUT_NODE = True

    # Progress segments
    PROGRESS_PREPARE = 20
    PROGRESS_SUBMIT = 30
    PROGRESS_POLL_END = 90

    @property
    def _log_prefix(self) -> str:
        return f"RH_OpenAPI_{self.__class__.__name__}"

    def _update_progress(self, pbar, value: int):
        if pbar:
            try:
                pbar.update_absolute(value, 100)
            except Exception:
                pass

    @classmethod
    @abstractmethod
    def INPUT_TYPES(cls) -> Dict:
        pass

    @abstractmethod
    def build_payload(self, **kwargs) -> Dict:
        pass

    def prepare_inputs(self, **kwargs) -> Dict:
        """Override in subclass: upload resources, etc."""
        return {}

    def process_result(self, result_urls: List[str]) -> tuple:
        """Override in subclass: download and convert to ComfyUI format."""
        raise NotImplementedError

    def execute(self, **kwargs):
        """
        Unified execution flow with contextual error reporting.

        Each stage wraps errors with the node name and stage info so users
        can identify exactly what went wrong and where.

        Returns:
            {"ui": {"text": [url, response]}, "result": (primary, url, response)}
        """
        api_config = kwargs.get("api_config")
        config = get_config(api_config)
        base_url = config["base_url"]
        api_key = config["api_key"]
        timeout = config["timeout"]
        polling_interval = config["polling_interval"]
        max_polling_time = config["max_polling_time"]

        pbar = comfy.utils.ProgressBar(100) if COMFYUI_AVAILABLE else None
        self._update_progress(pbar, 0)

        # Stage 1: Prepare inputs (upload media)
        try:
            prepared = self.prepare_inputs(**kwargs)
            kwargs.update(prepared)
        except Exception as e:
            raise RuntimeError(f"[{self._log_prefix}] Upload failed: {e}") from e
        self._update_progress(pbar, self.PROGRESS_PREPARE)

        # Stage 2: Build payload and submit task
        try:
            payload = self.build_payload(**kwargs)
            task_id = submit(
                self.ENDPOINT,
                payload,
                api_key,
                base_url,
                timeout=timeout,
                logger_prefix=self._log_prefix,
            )
        except Exception as e:
            raise RuntimeError(f"[{self._log_prefix}] Submit failed: {e}") from e
        self._update_progress(pbar, self.PROGRESS_SUBMIT)

        # Stage 3: Poll for results
        def on_progress(v):
            self._update_progress(pbar, v)

        try:
            result_urls, full_response = poll(
                task_id,
                api_key,
                base_url,
                polling_interval=polling_interval,
                max_polling_time=max_polling_time,
                on_progress=on_progress,
                logger_prefix=self._log_prefix,
            )
        except Exception as e:
            raise RuntimeError(f"[{self._log_prefix}] Task execution failed: {e}") from e
        self._update_progress(pbar, self.PROGRESS_POLL_END)

        # Stage 4: Download and process results
        try:
            primary_result = self.process_result(result_urls)
        except Exception as e:
            raise RuntimeError(f"[{self._log_prefix}] Result download failed: {e}") from e
        self._update_progress(pbar, 100)

        # Build extra outputs: url and response
        url_str = "\n".join(result_urls)
        response_str = json.dumps(full_response, ensure_ascii=False, indent=2)

        # Return with ui dict for OUTPUT_NODE history recording
        result_tuple = primary_result + (url_str, response_str)
        return {"ui": {"text": [url_str, response_str]}, "result": result_tuple}


class ImageToImageNodeBase(BaseNode):
    """Base for image-to-image: requires image upload."""

    OUTPUT_TYPE = "image"
    RETURN_TYPES = ("IMAGE", "STRING", "STRING")
    RETURN_NAMES = ("image", "url", "response")

    def prepare_inputs(self, **kwargs) -> Dict:
        image1 = kwargs.get("image1")
        if image1 is None:
            raise ValueError("image1 is required")
        config = get_config(kwargs.get("api_config"))
        img_bytes = tensor_to_bytes(image1)
        ext = "png"
        mime = "image/png"
        filename = f"upload_{hash(img_bytes) % 10**10}.{ext}"
        url = upload_file(
            img_bytes,
            filename,
            mime,
            config["api_key"],
            config["base_url"],
            timeout=config.get("upload_timeout", 60),
            logger_prefix=self._log_prefix,
        )
        return {"imageUrls": [url]}

    def process_result(self, result_urls: List[str]) -> tuple:
        if len(result_urls) > 5:
            print(f"[{self._log_prefix} WARNING] Results exceed 5, using first 5 only")
        batch = download_images_to_tensor(result_urls[:5], logger_prefix=self._log_prefix)
        return (batch,)


class TextToImageNodeBase(BaseNode):
    """Base for text-to-image: no upload required."""

    OUTPUT_TYPE = "image"
    RETURN_TYPES = ("IMAGE", "STRING", "STRING")
    RETURN_NAMES = ("image", "url", "response")

    def prepare_inputs(self, **kwargs) -> Dict:
        return {}

    def process_result(self, result_urls: List[str]) -> tuple:
        batch = download_images_to_tensor(result_urls[:5], logger_prefix=self._log_prefix)
        return (batch,)


class ImageToVideoNodeBase(BaseNode):
    """Base for image-to-video nodes: upload image, return video."""

    OUTPUT_TYPE = "video"
    RETURN_TYPES = ("VIDEO", "STRING", "STRING")
    RETURN_NAMES = ("video", "url", "response")

    def prepare_inputs(self, **kwargs) -> Dict:
        image = kwargs.get("image")
        if image is None:
            raise ValueError("image is required")
        config = get_config(kwargs.get("api_config"))
        img_bytes = tensor_to_bytes(image)
        filename = f"upload_{hash(img_bytes) % 10**10}.png"
        url = upload_file(
            img_bytes,
            filename,
            "image/png",
            config["api_key"],
            config["base_url"],
            timeout=config.get("upload_timeout", 60),
            logger_prefix=self._log_prefix,
        )
        return {"imageUrl": url}

    def process_result(self, result_urls: List[str]) -> tuple:
        if not result_urls:
            raise RuntimeError("No video URL in results")
        video = download_video(result_urls[0], logger_prefix=self._log_prefix)
        return (video,)


class TextToVideoNodeBase(BaseNode):
    """Base for text-to-video nodes: no upload, return video."""

    OUTPUT_TYPE = "video"
    RETURN_TYPES = ("VIDEO", "STRING", "STRING")
    RETURN_NAMES = ("video", "url", "response")

    def prepare_inputs(self, **kwargs) -> Dict:
        return {}

    def process_result(self, result_urls: List[str]) -> tuple:
        if not result_urls:
            raise RuntimeError("No video URL in results")
        video = download_video(result_urls[0], logger_prefix=self._log_prefix)
        return (video,)


class ReferenceToVideoNodeBase(BaseNode):
    """Base for reference-to-video nodes: upload reference image(s), return video."""

    OUTPUT_TYPE = "video"
    RETURN_TYPES = ("VIDEO", "STRING", "STRING")
    RETURN_NAMES = ("video", "url", "response")

    def prepare_inputs(self, **kwargs) -> Dict:
        return {}

    def process_result(self, result_urls: List[str]) -> tuple:
        if not result_urls:
            raise RuntimeError("No video URL in results")
        video = download_video(result_urls[0], logger_prefix=self._log_prefix)
        return (video,)


class AudioNodeBase(BaseNode):
    """Base for audio generation nodes: text-to-audio, music, voice clone."""

    OUTPUT_TYPE = "audio"
    RETURN_TYPES = ("AUDIO", "STRING", "STRING")
    RETURN_NAMES = ("audio", "url", "response")

    def prepare_inputs(self, **kwargs) -> Dict:
        return {}

    def process_result(self, result_urls: List[str]) -> tuple:
        if not result_urls:
            raise RuntimeError("No audio URL in results")
        audio = download_audio(result_urls[0], logger_prefix=self._log_prefix)
        return (audio,)


class ThreeDNodeBase(BaseNode):
    """Base for 3D model generation nodes."""

    OUTPUT_TYPE = "3d"
    RETURN_TYPES = ("STRING", "STRING", "STRING")
    RETURN_NAMES = ("model_url", "url", "response")

    def prepare_inputs(self, **kwargs) -> Dict:
        return {}

    def process_result(self, result_urls: List[str]) -> tuple:
        if not result_urls:
            raise RuntimeError("No 3D model URL in results")
        return (result_urls[0],)
