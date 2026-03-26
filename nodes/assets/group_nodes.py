"""
SparkVideo asset group management nodes.
"""

from ...core.rest import dumps_json
from .base import AssetRestNodeBase, clean_string, connectable_string_input, text_input


class RH_SparkVideoAssetGroupCreate(AssetRestNodeBase):
    ENDPOINT = "assets/groups/create"
    RETURN_TYPES = ("STRING", "STRING", "STRING", "STRING")
    RETURN_NAMES = ("group_id", "name", "description", "response")

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "name": text_input(),
            },
            "optional": {
                "description": text_input(),
                **cls.common_optional_inputs(),
            },
        }

    def build_payload(self, name, description="", **kwargs):
        payload = {"name": self._require_string("name", name)}
        description = clean_string(description)
        if description:
            payload["description"] = description
        return payload

    def parse_response(self, response, **kwargs):
        data = response.get("data") or {}
        return (
            clean_string(data.get("groupId")),
            clean_string(data.get("name")),
            clean_string(data.get("description")),
            self._response_json(response),
        )


class RH_SparkVideoAssetGroupList(AssetRestNodeBase):
    ENDPOINT = "assets/groups/list"
    RETURN_TYPES = ("STRING", "STRING", "STRING")
    RETURN_NAMES = ("items_json", "total_count", "response")

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "page_number": ("INT", {"default": 1, "min": 1, "max": 9999}),
                "page_size": ("INT", {"default": 20, "min": 1, "max": 100}),
            },
            "optional": {
                "name": text_input(),
                **cls.common_optional_inputs(),
            },
        }

    def build_payload(self, page_number, page_size, name="", **kwargs):
        payload = {
            "pageNumber": int(page_number),
            "pageSize": int(page_size),
        }
        name = clean_string(name)
        if name:
            payload["name"] = name
        return payload

    def parse_response(self, response, **kwargs):
        data = response.get("data") or {}
        items = data.get("items") or []
        return (
            dumps_json(items),
            clean_string(data.get("totalCount")),
            self._response_json(response),
        )


class RH_SparkVideoAssetGroupQuery(AssetRestNodeBase):
    ENDPOINT = "assets/groups/query"
    RETURN_TYPES = ("STRING", "STRING", "STRING", "STRING", "STRING")
    RETURN_NAMES = ("group_id", "name", "description", "asset_count", "response")

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "group_id": connectable_string_input(),
            },
            "optional": cls.common_optional_inputs(),
        }

    def build_payload(self, group_id, **kwargs):
        return {"groupId": self._require_string("group_id", group_id)}

    def parse_response(self, response, **kwargs):
        data = response.get("data") or {}
        return (
            clean_string(data.get("groupId")),
            clean_string(data.get("name")),
            clean_string(data.get("description")),
            clean_string(data.get("assetCount")),
            self._response_json(response),
        )


class RH_SparkVideoAssetGroupUpdate(AssetRestNodeBase):
    ENDPOINT = "assets/groups/update"
    RETURN_TYPES = ("STRING", "STRING", "STRING", "STRING")
    RETURN_NAMES = ("group_id", "name", "description", "response")

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "group_id": connectable_string_input(),
            },
            "optional": {
                "name": text_input(),
                "description": text_input(),
                **cls.common_optional_inputs(),
            },
        }

    def build_payload(self, group_id, name="", description="", **kwargs):
        payload = {"groupId": self._require_string("group_id", group_id)}
        name = clean_string(name)
        description = clean_string(description)
        if not name and not description:
            raise ValueError("At least one of name or description is required")
        if name:
            payload["name"] = name
        if description:
            payload["description"] = description
        return payload

    def parse_response(self, response, **kwargs):
        data = response.get("data") or {}
        return (
            clean_string(data.get("groupId")),
            clean_string(data.get("name")),
            clean_string(data.get("description")),
            self._response_json(response),
        )


class RH_SparkVideoAssetGroupDelete(AssetRestNodeBase):
    ENDPOINT = "assets/groups/delete"
    RETURN_TYPES = ("STRING", "STRING", "STRING")
    RETURN_NAMES = ("group_id", "status", "response")

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "group_id": connectable_string_input(),
            },
            "optional": cls.common_optional_inputs(),
        }

    def build_payload(self, group_id, **kwargs):
        return {"groupId": self._require_string("group_id", group_id)}

    def parse_response(self, response, group_id="", **kwargs):
        return (
            clean_string(group_id),
            "deleted",
            self._response_json(response),
        )
