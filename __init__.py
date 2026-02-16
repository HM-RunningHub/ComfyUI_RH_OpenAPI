"""
ComfyUI_RH_OpenAPI - RunningHub OpenAPI standard model nodes.

Provides 110+ API nodes for RunningHub's standard model endpoints,
covering image generation, video generation, audio synthesis, and 3D modeling.
"""

from .nodes.settings_node import RHSettingsNode
from .nodes.node_factory import create_all_nodes

# Generate all API nodes from registry
_class_mappings, _display_mappings = create_all_nodes()

NODE_CLASS_MAPPINGS = {
    "RHSettingsNode": RHSettingsNode,
    **_class_mappings,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "RHSettingsNode": "RH OpenAPI Settings",
    **_display_mappings,
}

__all__ = ["NODE_CLASS_MAPPINGS", "NODE_DISPLAY_NAME_MAPPINGS"]
