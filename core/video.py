"""
Video download utilities.
"""

import os
import uuid
import requests
from typing import Optional, Tuple, Any

# ComfyUI dependency (optional)
try:
    import folder_paths
    from comfy_api.input_impl import VideoFromFile
    COMFYUI_AVAILABLE = True
except ImportError:
    COMFYUI_AVAILABLE = False
    folder_paths = None
    VideoFromFile = None


def download_video(
    url: str,
    timeout: int = 180,
    max_retries: int = 3,
    logger_prefix: str = "RH_OpenAPI_Video",
) -> Any:
    """
    Download video from URL → VideoFromFile or local path.

    Returns:
        VideoFromFile(path) or path when ComfyUI is not available.
    """
    if COMFYUI_AVAILABLE and folder_paths:
        output_dir = folder_paths.get_output_directory()
    else:
        output_dir = os.environ.get("RH_OUTPUT_DIR", "/tmp")

    filename = f"rh_{uuid.uuid4()}.mp4"
    video_path = os.path.join(output_dir, filename)

    last_error = None
    for attempt in range(max_retries):
        try:
            if attempt > 0:
                import time
                time.sleep(2 ** attempt)
            response = requests.get(url, stream=True, timeout=timeout)
            response.raise_for_status()
            with open(video_path, "wb") as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            if COMFYUI_AVAILABLE and VideoFromFile:
                return VideoFromFile(video_path)
            return video_path
        except Exception as e:
            last_error = e
            continue

    raise RuntimeError(f"Failed to download video after {max_retries} attempts: {last_error}")
