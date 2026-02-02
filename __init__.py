"""
ComfyUI_RH_OpenAPI - RunningHub OpenAPI standard model nodes.
"""

from .nodes.settings_node import RHSettingsNode
from .nodes.image_to_image.banana_i2i import BananaI2I

NODE_CLASS_MAPPINGS = {
    "RHSettingsNode": RHSettingsNode,
    "BananaI2I": BananaI2I,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "RHSettingsNode": "RH OpenAPI Settings",
    "BananaI2I": "RH Banana Image-to-Image",
}

__all__ = ["NODE_CLASS_MAPPINGS", "NODE_DISPLAY_NAME_MAPPINGS"]
