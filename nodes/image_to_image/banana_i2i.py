"""
Banana image-to-image - rhart-image-v1/edit
"""

from ...core.base import ImageToImageNodeBase
from ...core.api_key import get_config
from ...core.upload import upload_file
from ...core.image import tensor_to_bytes

ASPECT_RATIOS = [
    "auto", "1:1", "16:9", "9:16", "4:3", "3:4",
    "3:2", "2:3", "5:4", "4:5", "21:9"
]


class BananaI2I(ImageToImageNodeBase):
    """Banana image-to-image - rhart-image-v1/edit. Up to 5 images (image1 required, image2-5 optional)."""

    ENDPOINT = "rhart-image-v1/edit"
    CATEGORY = "RunningHub/image-to-image"

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "prompt": ("STRING", {"multiline": True}),
                "image1": ("IMAGE",),
            },
            "optional": {
                "image2": ("IMAGE",),
                "image3": ("IMAGE",),
                "image4": ("IMAGE",),
                "image5": ("IMAGE",),
                "api_config": ("STRUCT",),
                "aspect_ratio": (ASPECT_RATIOS, {"default": "auto"}),
            }
        }

    @classmethod
    def VALIDATE_INPUTS(cls, prompt, image1, aspect_ratio="auto", **kwargs):
        if aspect_ratio not in ASPECT_RATIOS:
            return f"Invalid aspect_ratio: {aspect_ratio}. Must be one of: {', '.join(ASPECT_RATIOS)}"
        return True

    def prepare_inputs(self, **kwargs) -> dict:
        """Upload image1 (required) and image2-5 (optional); combine into imageUrls."""
        config = get_config(kwargs.get("api_config"))
        image_urls = []
        for i in range(1, 6):
            img = kwargs.get(f"image{i}")
            if img is None:
                continue
            img_bytes = tensor_to_bytes(img)
            ext = "png"
            mime = "image/png"
            filename = f"upload_{hash(img_bytes) % 10**10}_{i}.{ext}"
            url = upload_file(
                img_bytes,
                filename,
                mime,
                config["api_key"],
                config["base_url"],
                timeout=config.get("upload_timeout", 60),
                logger_prefix=self._log_prefix,
            )
            image_urls.append(url)
        if not image_urls:
            raise ValueError("At least image1 is required")
        return {"imageUrls": image_urls}

    def build_payload(self, prompt, image1, aspect_ratio="auto", **kwargs):
        image_urls = kwargs.get("imageUrls", [])
        if not image_urls:
            raise ValueError("imageUrls is required (from image upload)")
        return {
            "prompt": prompt.strip(),
            "aspectRatio": aspect_ratio,
            "imageUrls": image_urls,
        }
