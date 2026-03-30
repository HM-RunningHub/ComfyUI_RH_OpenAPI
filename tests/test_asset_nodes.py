import importlib
import json
import sys
import threading
import time
import unittest
from pathlib import Path
from types import ModuleType
from unittest.mock import patch


PROJECT_ROOT = Path(__file__).resolve().parents[1]


class SparkVideoAssetCreateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        package_name = "asset_nodes_test_pkg"
        if package_name not in sys.modules:
            module = ModuleType(package_name)
            module.__path__ = [str(PROJECT_ROOT)]
            sys.modules[package_name] = module
        cls.asset_nodes = importlib.import_module(f"{package_name}.nodes.assets.asset_nodes")

    def test_multimedia_inputs_run_in_parallel_and_merge_in_input_order(self):
        node = self.asset_nodes.RH_SparkVideoAssetCreate()
        image = object()
        video = object()
        audio = object()
        fake_config = {"api_key": "test-key", "base_url": "https://example.com"}
        barrier = threading.Barrier(3)
        created_at = {}
        delays = {"image": 0.12, "video": 0.01, "audio": 0.06}
        asset_ids_by_type = {"image": "img-1", "video": "vid-2", "audio": "aud-3"}
        statuses_by_type = {"image": "ACTIVE", "video": "READY", "audio": "ACTIVE"}

        def fake_create_asset(config, media_type, media_value, logger_prefix):
            self.assertIs(config, fake_config)
            created_at[media_type] = time.perf_counter()
            barrier.wait(timeout=1.0)
            time.sleep(delays[media_type])
            asset_id = asset_ids_by_type[media_type]
            return {
                "asset_id": asset_id,
                "asset_url": f"asset://{asset_id}",
                "status": statuses_by_type[media_type],
                "response": {"data": {"assetId": asset_id}},
            }

        with patch.object(self.asset_nodes, "get_config", return_value=fake_config), patch.object(
            self.asset_nodes,
            "create_fixed_asset_from_media",
            side_effect=fake_create_asset,
        ) as create_mock:
            asset_ids, status, response = node.execute(
                api_config={},
                image=image,
                video=video,
                audio=audio,
            )

        self.assertEqual(asset_ids, "img-1, vid-2, aud-3")
        self.assertEqual(status, "ACTIVE, READY")

        payload = json.loads(response)
        self.assertEqual(payload["data"]["assetId"], asset_ids)
        self.assertEqual(payload["data"]["assetIds"], ["img-1", "vid-2", "aud-3"])
        self.assertEqual(payload["data"]["count"], 3)
        self.assertEqual(
            [item["media_type"] for item in payload["data"]["items"]],
            ["image", "video", "audio"],
        )

        self.assertEqual(create_mock.call_count, 3)
        self.assertEqual(
            create_mock.call_args_list[0].args,
            (fake_config, "image", image, "RH_OpenAPI_RH_SparkVideoAssetCreate_Image"),
        )
        self.assertEqual(
            create_mock.call_args_list[1].args,
            (fake_config, "video", video, "RH_OpenAPI_RH_SparkVideoAssetCreate_Video"),
        )
        self.assertEqual(
            create_mock.call_args_list[2].args,
            (fake_config, "audio", audio, "RH_OpenAPI_RH_SparkVideoAssetCreate_Audio"),
        )
        self.assertLess(max(created_at.values()) - min(created_at.values()), 0.2)

    def test_multimedia_inputs_keep_skip_error_behavior(self):
        node = self.asset_nodes.RH_SparkVideoAssetCreate()
        fake_config = {"api_key": "test-key", "base_url": "https://example.com"}

        with patch.object(self.asset_nodes, "get_config", return_value=fake_config), patch.object(
            self.asset_nodes,
            "create_fixed_asset_from_media",
            side_effect=RuntimeError("upload failed"),
        ):
            asset_ids, status, response = node.execute(
                api_config={},
                image=object(),
                video=object(),
                skip_error=True,
            )

        self.assertEqual(asset_ids, "")
        self.assertEqual(status, "")
        self.assertIn(
            "RH_OpenAPI_RH_SparkVideoAssetCreate: upload failed",
            json.loads(response)["error"],
        )


if __name__ == "__main__":
    unittest.main()
