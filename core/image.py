"""
Image utilities: tensor ↔ PIL, download images.
"""

import random
import time
import numpy as np
import torch
import requests
from typing import List, Union, Optional
from io import BytesIO
from PIL import Image, UnidentifiedImageError


def tensor_to_pil(image: torch.Tensor) -> List[Image.Image]:
    """ComfyUI tensor [B,H,W,C] or [H,W,C] → list of PIL Images."""
    if image is None:
        return []
    if hasattr(image, "cpu"):
        image = image.cpu()
    arr = image.numpy() if hasattr(image, "numpy") else np.array(image)
    if len(arr.shape) == 3:
        arr = arr[np.newaxis, ...]
    images = []
    for i in range(arr.shape[0]):
        img = arr[i]
        if len(img.shape) == 3 and img.shape[0] in (1, 3, 4) and img.shape[2] not in (1, 3, 4):
            img = np.transpose(img, (1, 2, 0))
        if img.max() <= 1.0:
            img = (img * 255).astype(np.uint8)
        else:
            img = img.astype(np.uint8)
        if len(img.shape) == 2:
            pil_img = Image.fromarray(img, mode="L")
        elif img.shape[2] == 4:
            pil_img = Image.fromarray(img, mode="RGBA")
        else:
            pil_img = Image.fromarray(img, mode="RGB")
        images.append(pil_img)
    return images


def pil_to_tensor(images: Union[Image.Image, List[Image.Image]]) -> torch.Tensor:
    """PIL or list of PIL → ComfyUI tensor [B,H,W,C], value range [0,1]."""
    if isinstance(images, Image.Image):
        images = [images]
    tensors = []
    for img in images:
        if img.mode != "RGB":
            img = img.convert("RGB")
        arr = np.array(img).astype(np.float32) / 255.0
        tensors.append(torch.from_numpy(arr))
    return torch.stack(tensors)


def tensor_to_bytes(image: torch.Tensor, format: str = "PNG") -> bytes:
    """Convert tensor to bytes for upload."""
    pils = tensor_to_pil(image)
    if not pils:
        raise ValueError("Empty image")
    buf = BytesIO()
    pils[0].save(buf, format=format)
    return buf.getvalue()


def download_image(
    url: str,
    timeout: int = 60,
    max_retries: int = 10,
    initial_backoff: float = 1,
    logger_prefix: str = "RH_OpenAPI_Image",
) -> Optional[Image.Image]:
    """Download image from URL → PIL Image."""
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept": "image/*",
    }
    last_error = None
    for attempt in range(max_retries):
        try:
            response = requests.get(url, headers=headers, timeout=timeout)
            response.raise_for_status()
            img = Image.open(BytesIO(response.content))
            return img.convert("RGB")
        except Exception as e:
            last_error = e
            if attempt < max_retries - 1:
                backoff = min(initial_backoff * (2 ** attempt) + random.uniform(0, 1), 30)
                time.sleep(backoff)
    print(f"[{logger_prefix} ERROR] Download failed after {max_retries} attempts: {last_error}")
    return None


def download_images_to_tensor(
    urls: List[str],
    logger_prefix: str = "RH_OpenAPI_Image",
) -> torch.Tensor:
    """Download multiple URLs and merge into batch tensor [N,H,W,C]."""
    images = []
    for url in urls:
        pil = download_image(url, logger_prefix=logger_prefix)
        if pil is None:
            raise RuntimeError(f"Failed to download image from URL")
        images.append(pil)
    if not images:
        raise RuntimeError("No images to convert")
    return pil_to_tensor(images)
