"""
RH OpenAPI Settings node.

Outputs base_url and apiKey for API nodes. Format compatible with ComfyUI_RH_APICall.
"""


class RHSettingsNode:
    """RH OpenAPI Settings"""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                # Default: production OpenAPI v2 base URL
                "base_url": ("STRING", {"default": "https://www.runninghub.cn/openapi/v2"}),
                "apiKey": ("STRING", {"default": ""}),
            },
        }

    RETURN_TYPES = ("RH_OPENAPI_CONFIG",)
    RETURN_NAMES = ("api_config",)
    CATEGORY = "RunningHub"
    FUNCTION = "process"

    def process(self, base_url, apiKey):
        return [{"base_url": base_url, "apiKey": apiKey}]
