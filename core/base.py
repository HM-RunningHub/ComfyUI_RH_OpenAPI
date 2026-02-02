"""
Base classes for API nodes.

Unified flow: prepare_inputs → build_payload → submit → poll → process_result
"""

import time
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

from .api_key import get_config
from .upload import upload_file
from .task import submit, poll
from .image import tensor_to_bytes, download_images_to_tensor
from .video import download_video

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
    OUTPUT_TYPE: str = "image"  # "image" | "video"
    CATEGORY: str = "RunningHub"
    FUNCTION: str = "execute"

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

    def process_result(self, result_urls: List[str]) -> Any:
        """Override in subclass: download and convert to ComfyUI format."""
        raise NotImplementedError

    def execute(self, **kwargs):
        api_config = kwargs.get("api_config")
        config = get_config(api_config)
        base_url = config["base_url"]
        api_key = config["api_key"]
        timeout = config["timeout"]
        polling_interval = config["polling_interval"]
        max_polling_time = config["max_polling_time"]

        pbar = comfy.utils.ProgressBar(100) if COMFYUI_AVAILABLE else None
        self._update_progress(pbar, 0)

        prepared = self.prepare_inputs(**kwargs)
        kwargs.update(prepared)
        self._update_progress(pbar, self.PROGRESS_PREPARE)

        payload = self.build_payload(**kwargs)
        task_id = submit(
            self.ENDPOINT,
            payload,
            api_key,
            base_url,
            timeout=timeout,
            logger_prefix=self._log_prefix,
        )
        self._update_progress(pbar, self.PROGRESS_SUBMIT)

        def on_progress(v):
            self._update_progress(pbar, v)

        result_urls = poll(
            task_id,
            api_key,
            base_url,
            polling_interval=polling_interval,
            max_polling_time=max_polling_time,
            on_progress=on_progress,
            logger_prefix=self._log_prefix,
        )
        self._update_progress(pbar, self.PROGRESS_POLL_END)

        result = self.process_result(result_urls)
        self._update_progress(pbar, 100)
        return result


class ImageToImageNodeBase(BaseNode):
    """Base for image-to-image: requires image upload."""

    OUTPUT_TYPE = "image"
    RETURN_TYPES = ("IMAGE",)
    RETURN_NAMES = ("image",)

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
    RETURN_TYPES = ("IMAGE",)
    RETURN_NAMES = ("image",)

    def prepare_inputs(self, **kwargs) -> Dict:
        return {}

    def process_result(self, result_urls: List[str]) -> tuple:
        batch = download_images_to_tensor(result_urls[:5], logger_prefix=self._log_prefix)
        return (batch,)


class ImageToVideoNodeBase(BaseNode):
    """Base for image-to-video nodes."""

    OUTPUT_TYPE = "video"
    RETURN_TYPES = ("VIDEO", "VIDEO", "VIDEO", "VIDEO", "VIDEO")
    RETURN_NAMES = ("video1", "video2", "video3", "video4", "video5")

    def process_result(self, result_urls: List[str]) -> tuple:
        videos = []
        for i, url in enumerate(result_urls[:5]):
            v = download_video(url, logger_prefix=self._log_prefix)
            videos.append(v)
        while len(videos) < 5:
            videos.append(None)
        return tuple(videos[:5])
