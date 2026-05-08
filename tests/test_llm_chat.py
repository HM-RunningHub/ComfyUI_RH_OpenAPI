import importlib
import sys
import unittest
from pathlib import Path
from types import ModuleType, SimpleNamespace
from unittest.mock import patch


PROJECT_ROOT = Path(__file__).resolve().parents[1]

package_name = "llm_chat_test_pkg"
if package_name not in sys.modules:
    module = ModuleType(package_name)
    module.__path__ = [str(PROJECT_ROOT)]
    sys.modules[package_name] = module

llm_chat = importlib.import_module(f"{package_name}.nodes.llm_chat")


class LLMChatNodeTests(unittest.TestCase):
    def setUp(self):
        llm_chat._MODEL_CACHE["models"] = None
        llm_chat._MODEL_CACHE["expires_at"] = 0.0

    def test_fetch_llm_models_uses_fallback_on_request_failure(self):
        with patch.object(llm_chat.requests, "get", side_effect=RuntimeError("offline")):
            models = llm_chat.fetch_llm_models(force=True)

        self.assertEqual(models, llm_chat.FALLBACK_MODELS)

    def test_fetch_llm_models_reads_ids_from_response(self):
        response = SimpleNamespace(
            raise_for_status=lambda: None,
            json=lambda: {
                "data": [
                    {"id": "qwen/qwen-plus"},
                    {"id": "deepseek/deepseek-v3.2"},
                    {"object": "model"},
                ]
            },
        )

        with patch.object(llm_chat.requests, "get", return_value=response) as get:
            models = llm_chat.fetch_llm_models(force=True)

        self.assertEqual(models, ["qwen/qwen-plus", "deepseek/deepseek-v3.2"])
        get.assert_called_once_with("https://llm.runninghub.ai/v1/models", timeout=5)

    def test_build_chat_payload_omits_random_seed(self):
        payload = llm_chat.build_chat_payload(
            "qwen/qwen-plus",
            [{"role": "user", "content": "hello"}],
            0.6,
            llm_chat.DEFAULT_MAX_TOKENS,
            1.0,
            0.0,
            0.0,
            "none",
            -1,
        )

        self.assertNotIn("seed", payload)

    def test_build_chat_payload_does_not_forward_seed(self):
        payload = llm_chat.build_chat_payload(
            "qwen/qwen-plus",
            [{"role": "user", "content": "hello"}],
            0.6,
            2048,
            0.8,
            0.2,
            0.1,
            "low",
            123,
        )

        self.assertNotIn("seed", payload)
        self.assertEqual(payload["max_tokens"], 2048)
        self.assertEqual(payload["top_p"], 0.8)
        self.assertEqual(payload["presence_penalty"], 0.2)
        self.assertEqual(payload["frequency_penalty"], 0.1)
        self.assertEqual(payload["reasoning_effort"], "low")
        self.assertNotIn("extra_body", payload)

    def test_build_messages_prefers_images_over_video(self):
        with patch.object(llm_chat, "_encode_video", side_effect=AssertionError("video should be ignored")):
            messages = llm_chat.build_messages("system", "prompt", ["https://example.com/image.jpg"], video=object())

        user_content = messages[1]["content"]
        self.assertEqual(user_content[0], {"type": "text", "text": "prompt"})
        self.assertEqual(user_content[1]["type"], "image_url")
        self.assertEqual(user_content[1]["image_url"]["url"], "https://example.com/image.jpg")

    def test_upload_images_converts_tensor_and_calls_upload(self):
        config = {
            "api_key": "test-key",
            "base_url": "https://www.runninghub.cn/openapi/v2",
            "upload_timeout": 5,
        }

        with (
            patch.object(llm_chat, "_image_to_jpeg_bytes", return_value=[b"jpeg"]) as convert,
            patch.object(llm_chat, "upload_file", return_value="https://example.com/upload.jpg") as upload,
        ):
            urls = llm_chat.upload_images([object()], config)

        self.assertEqual(urls, ["https://example.com/upload.jpg"])
        convert.assert_called_once()
        self.assertEqual(upload.call_args.args[1], "rh_llm_image_1.jpg")
        self.assertEqual(upload.call_args.args[2], "image/jpeg")

    def test_public_node_has_no_balance_validation_hook(self):
        self.assertFalse(hasattr(llm_chat.RHLLMChatNode, "VALIDATE_INPUTS"))

    def test_api_config_is_last_optional_input(self):
        with patch.object(llm_chat, "fetch_llm_models", return_value=["qwen/qwen-plus"]):
            inputs = llm_chat.RHLLMChatNode.INPUT_TYPES()
            required_keys = list(inputs["required"].keys())
            optional_keys = list(inputs["optional"].keys())

        self.assertEqual(
            required_keys,
            [
                "model",
                "role",
                "prompt",
                "temperature",
                "max_tokens",
                "top_p",
                "presence_penalty",
                "frequency_penalty",
                "reasoning_effort",
                "seed",
            ],
        )
        self.assertEqual(optional_keys[-1], "api_config")

    def test_chat_uses_cn_endpoint_and_retries_upstream_error(self):
        responses = [
            SimpleNamespace(
                status_code=502,
                text='{"error":{"message":"upstream failed"}}',
                json=lambda: {"error": {"message": "upstream failed"}},
            ),
            SimpleNamespace(
                status_code=200,
                text="",
                json=lambda: {"choices": [{"message": {"content": "ok"}}]},
            ),
        ]

        with patch.object(llm_chat.requests, "post", side_effect=responses) as post:
            with patch.object(llm_chat.time, "sleep"):
                data = llm_chat.post_chat_completion({}, {"model": "qwen/qwen-plus"}, 30)

        self.assertEqual(data["choices"][0]["message"]["content"], "ok")
        self.assertEqual(post.call_count, 2)
        self.assertEqual(post.call_args_list[0].args[0], "https://llm.runninghub.cn/v1/chat/completions")


if __name__ == "__main__":
    unittest.main()
