"""
Base helpers for SparkVideo asset management nodes.
"""

import json
from typing import Any, Dict

from ...core.api_key import get_config
from ...core.rest import dumps_json, post_json


ASSET_CATEGORY = "RunningHub/SparkVideo Assets"


def text_input(default: str = "", multiline: bool = False) -> tuple:
    options = {"default": default}
    if multiline:
        options["multiline"] = True
    return ("STRING", options)


def connectable_string_input() -> tuple:
    return ("STRING", {"default": "", "forceInput": True})


def clean_string(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


class AssetRestNodeBase:
    CATEGORY = ASSET_CATEGORY
    FUNCTION = "execute"
    OUTPUT_NODE = True
    RETURN_TYPES = ("STRING", "STRING")
    RETURN_NAMES = ("result", "response")
    ENDPOINT = ""

    @property
    def _log_prefix(self) -> str:
        return f"RH_OpenAPI_{self.__class__.__name__}"

    @classmethod
    def common_optional_inputs(cls) -> Dict[str, tuple]:
        return {
            "api_config": ("RH_OPENAPI_CONFIG",),
            "skip_error": ("BOOLEAN", {"default": False}),
        }

    def build_payload(self, **kwargs) -> Dict[str, Any]:
        raise NotImplementedError

    def prepare_payload(self, config: Dict[str, Any], **kwargs) -> Dict[str, Any]:
        return self.build_payload(**kwargs)

    def request(self, config: Dict[str, Any], payload: Dict[str, Any]) -> Dict[str, Any]:
        return post_json(
            self.ENDPOINT,
            payload,
            config["api_key"],
            config["base_url"],
            timeout=config.get("timeout", 60),
            logger_prefix=self._log_prefix,
        )

    def parse_response(self, response: Dict[str, Any], **kwargs):
        raise NotImplementedError

    def _require_string(self, field_name: str, value: Any) -> str:
        text = clean_string(value)
        if not text:
            raise ValueError(f"{field_name} is required")
        return text

    def _response_json(self, response: Dict[str, Any]) -> str:
        return dumps_json(response)

    def _error_result(self, error_msg: str):
        payload = json.dumps({"error": error_msg}, ensure_ascii=False, indent=2)
        values = [""] * len(self.RETURN_TYPES)
        values[-1] = payload
        return tuple(values)

    def execute(self, **kwargs):
        skip_error = kwargs.pop("skip_error", False)
        try:
            config = get_config(kwargs.get("api_config"))
            payload = self.prepare_payload(config, **kwargs)
            response = self.request(config, payload)
            return self.parse_response(response, config=config, **kwargs)
        except Exception as e:
            if skip_error:
                return self._error_result(f"{self._log_prefix}: {e}")
            raise
