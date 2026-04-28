"""Conformance tests for the RunningHub AI integration kit.

These tests do not call the real RunningHub API. They validate contract behavior
that AI-generated client code should preserve.
"""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Any, Dict, List, Mapping


KIT_ROOT = Path(__file__).resolve().parents[1]
PYTHON_EXAMPLES = KIT_ROOT / "examples" / "python"
sys.path.insert(0, str(PYTHON_EXAMPLES))

from client import (  # noqa: E402
    RHResult,
    RunningHubClient,
    RunningHubError,
    build_multipart_body,
    extract_outputs,
    find_model,
    is_retryable_http_error,
    load_registry,
    validate_payload,
)


class FakeRunningHubClient(RunningHubClient):
    def __init__(self, responses: List[Dict[str, Any]]) -> None:
        super().__init__(api_key="test-key", polling_interval=0, max_polling_time=5)
        self.responses = responses
        self.requests: List[Dict[str, Any]] = []

    def _request_json(
        self,
        method: str,
        url: str,
        body: bytes,
        headers: Mapping[str, str],
        retryable: bool,
    ) -> Dict[str, Any]:
        self.requests.append(
            {
                "method": method,
                "url": url,
                "body": body,
                "headers": dict(headers),
                "retryable": retryable,
            }
        )
        if not self.responses:
            raise RunningHubError("No fake response left")
        return self.responses.pop(0)


class ContractTests(unittest.TestCase):
    def test_public_registry_is_valid_full_catalog_and_public_safe(self) -> None:
        registry = load_registry(KIT_ROOT / "model-registry.public.json")
        self.assertGreaterEqual(registry["model_count"], 294)
        self.assertEqual(registry["model_count"], len(registry["models"]))
        forbidden_keys = {"internal_name", "price_badge", "price_badge_meta", "billing", "billing_spec"}
        endpoints = set()
        for model in registry["models"]:
            self.assertTrue(model.get("endpoint"))
            self.assertIn("output_type", model)
            self.assertIn("params", model)
            self.assertFalse(forbidden_keys.intersection(model.keys()))
            endpoints.add(model["endpoint"])
        self.assertIn("rhart-image-v1/text-to-image", endpoints)
        self.assertIn("rhart-video-v3.1-fast/text-to-video", endpoints)

    def test_public_pricing_is_structured_and_public_safe(self) -> None:
        pricing = load_registry(KIT_ROOT / "pricing.public.json")
        self.assertGreaterEqual(pricing["pricing_count"], 290)
        self.assertEqual(pricing["pricing_count"], len(pricing["pricing"]))

        serialized = json.dumps(pricing, ensure_ascii=False)
        forbidden_terms = [
            "price_badge",
            "price_badge_meta",
            "price_base_id",
            "billing_adapter_class_name",
            "jsonata",
            "$round",
            "$lookup",
        ]
        for term in forbidden_terms:
            self.assertNotIn(term, serialized)

        by_endpoint = {entry["endpoint"]: entry for entry in pricing["pricing"]}
        fixed = by_endpoint["rhart-image-v1/text-to-image"]
        self.assertEqual(fixed["pricing_type"], "fixed")
        self.assertEqual(fixed["currency"], "CNY")
        self.assertEqual(fixed["price"], 0.05)

        parameter_based = by_endpoint["rhart-video-v3.1-fast/text-to-video"]
        self.assertEqual(parameter_based["pricing_type"], "parameter_based")
        self.assertEqual(parameter_based["depends_on"], ["resolution"])
        self.assertIn({"when": {"resolution": "720p"}, "price": 0.2}, parameter_based["rules"])

    def test_registry_sample_is_valid_and_has_required_model_shapes(self) -> None:
        registry = load_registry(KIT_ROOT / "model-registry.sample.json")
        self.assertGreaterEqual(len(registry["models"]), 4)
        for model in registry["models"]:
            self.assertIn("endpoint", model)
            self.assertIn("output_type", model)
            self.assertIn("params", model)
            for param in model["params"]:
                self.assertIn("fieldKey", param)
                self.assertIn("type", param)
                self.assertIn("required", param)

    def test_payload_validation_rejects_missing_required_and_invalid_enum(self) -> None:
        registry = load_registry(KIT_ROOT / "model-registry.sample.json")
        model = find_model(registry, "rhart-image-v1/text-to-image")

        with self.assertRaises(RunningHubError):
            validate_payload(model, {"aspectRatio": "1:1"})

        with self.assertRaises(RunningHubError):
            validate_payload(model, {"prompt": "cat", "aspectRatio": "square"})

        validate_payload(model, {"prompt": "cat", "aspectRatio": "1:1"})

    def test_submit_uses_bearer_auth_and_extracts_task_id(self) -> None:
        client = FakeRunningHubClient([{"taskId": "task-123"}])
        task_id = client.submit("rhart-image-v1/text-to-image", {"prompt": "cat"})

        self.assertEqual(task_id, "task-123")
        request = client.requests[0]
        self.assertEqual(request["headers"]["Authorization"], "Bearer test-key")
        self.assertEqual(request["headers"]["Content-Type"], "application/json")
        self.assertIn(b'"prompt": "cat"', request["body"])

    def test_poll_handles_non_terminal_then_success(self) -> None:
        client = FakeRunningHubClient(
            [
                {"status": "CREATE"},
                {"status": "RUNNING"},
                {"status": "SUCCESS", "results": [{"url": "https://example.com/out.png"}]},
            ]
        )

        response = client.poll("task-123")
        self.assertEqual(response["status"], "SUCCESS")
        self.assertEqual(len(client.requests), 3)
        for request in client.requests:
            self.assertEqual(json.loads(request["body"].decode("utf-8")), {"taskId": "task-123"})

    def test_run_returns_task_id_outputs_and_raw_response(self) -> None:
        client = FakeRunningHubClient(
            [
                {"taskId": "task-123"},
                {"status": "SUCCESS", "results": [{"url": "https://example.com/out.png"}]},
            ]
        )

        result = client.run("rhart-image-v1/text-to-image", {"prompt": "cat", "aspectRatio": "1:1"})
        self.assertIsInstance(result, RHResult)
        self.assertEqual(result.task_id, "task-123")
        self.assertEqual(result.outputs, ["https://example.com/out.png"])
        self.assertEqual(result.raw_response["status"], "SUCCESS")

    def test_extract_outputs_supports_url_and_text_shapes(self) -> None:
        response = {
            "results": [
                {"outputUrl": "https://example.com/video.mp4"},
                {"content": "hello"},
            ]
        }
        self.assertEqual(extract_outputs(response), ["https://example.com/video.mp4", "hello"])

    def test_retry_policy_only_retries_429_and_5xx_http_errors(self) -> None:
        self.assertTrue(is_retryable_http_error(429, "rate limit"))
        self.assertTrue(is_retryable_http_error(500, "server error"))
        self.assertFalse(is_retryable_http_error(400, "invalid parameter"))
        self.assertFalse(is_retryable_http_error(401, "unauthorized"))
        self.assertFalse(is_retryable_http_error(403, "forbidden"))

    def test_multipart_upload_body_uses_file_field(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "input.png"
            path.write_bytes(b"fake-image")
            body = build_multipart_body("boundary", path, "image/png")

        self.assertIn(b'name="file"; filename="input.png"', body)
        self.assertIn(b"Content-Type: image/png", body)
        self.assertIn(b"fake-image", body)


if __name__ == "__main__":
    unittest.main()
