import importlib
import json
import sys
import unittest
from pathlib import Path
from types import ModuleType


PROJECT_ROOT = Path(__file__).resolve().parents[1]
REGISTRY_PATH = PROJECT_ROOT / "models_registry.json"


class RealPersonModeDefaultTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with REGISTRY_PATH.open("r", encoding="utf-8") as handle:
            registry = json.load(handle)
        cls.models_by_name = {
            model["internal_name"]: model
            for model in registry
            if model.get("internal_name")
        }
        package_name = "real_person_mode_defaults_test_pkg"
        if package_name not in sys.modules:
            module = ModuleType(package_name)
            module.__path__ = [str(PROJECT_ROOT)]
            sys.modules[package_name] = module
        cls.node_factory = importlib.import_module(f"{package_name}.nodes.node_factory")

    def build_node_class(self, internal_name: str):
        return self.node_factory.create_node_class(self.models_by_name[internal_name])

    def test_supported_sparkvideo_nodes_default_real_person_mode_to_enabled(self):
        supported_nodes = [
            "RH_RhartVideoSparkvideo20ImageToVideo",
            "RH_RhartVideoSparkvideo20FastImageToVideo",
            "RH_RhartVideoSparkvideo20MultimodalVideo",
            "RH_RhartVideoSparkvideo20FastMultimodalVideo",
        ]

        for internal_name in supported_nodes:
            with self.subTest(internal_name=internal_name):
                node_class = self.build_node_class(internal_name)
                optional_inputs = node_class.INPUT_TYPES()["optional"]
                self.assertIn("real_person_mode", optional_inputs)
                self.assertTrue(optional_inputs["real_person_mode"][1]["default"])

    def test_real_person_mode_is_not_exposed_without_asset_slots(self):
        unsupported_nodes = [
            "RH_RhartVideoSparkvideo20TextToVideo",
            "RH_RhartVideoSparkvideo20FastTextToVideo",
        ]

        for internal_name in unsupported_nodes:
            with self.subTest(internal_name=internal_name):
                node_class = self.build_node_class(internal_name)
                optional_inputs = node_class.INPUT_TYPES()["optional"]
                self.assertNotIn("real_person_mode", optional_inputs)


if __name__ == "__main__":
    unittest.main()
