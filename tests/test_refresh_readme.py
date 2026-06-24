import importlib.util
import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

PROJECT_ROOT = Path(__file__).resolve().parents[1]
REFRESH_README_PATH = PROJECT_ROOT / "scripts" / "refresh_readme.py"
SPEC = importlib.util.spec_from_file_location("project_refresh_readme", REFRESH_README_PATH)
refresh_readme = importlib.util.module_from_spec(SPEC)
assert SPEC is not None and SPEC.loader is not None
SPEC.loader.exec_module(refresh_readme)


ZH_TEMPLATE = """# ComfyUI_RH_OpenAPI

![License](https://img.shields.io/badge/License-Apache%202.0-green)
![Nodes](https://img.shields.io/badge/Nodes-1-blue)

本项目当前收录 2 个标准模型 API 节点，总计提供 3 个 ComfyUI 节点。

- **节点总量** — 共 4 个 ComfyUI 节点，其中包含 5 个标准模型节点、3 个 Seedance2.0 素材节点、1 个 RunningHub LLM 对话节点和 1 个设置节点

项目在 `examples/` 目录下提供了 6 个示例工作流 JSON 文件。

```
├── models_registry.json     # 模型注册表（7 个模型定义）
└── examples/                # 8 个示例工作流
```

## 支持的模型

### 图像生成（900 个节点）
### 视频生成（901 个节点）
### 文本理解（902 个节点）
### 音频合成（903 个节点）
### 3D 建模（904 个节点）
### Seedance2.0 素材资产（905 个节点）
"""

EN_TEMPLATE = """# ComfyUI_RH_OpenAPI

![License](https://img.shields.io/badge/License-Apache%202.0-green)
![Nodes](https://img.shields.io/badge/Nodes-1-blue)

The project currently includes 2 standard model API nodes ... it provides 3 ComfyUI nodes in total.

- **Node Count** — 4 ComfyUI nodes in total: 5 standard model nodes, 3 Seedance2.0 asset nodes, 1 RunningHub LLM chat node, and 1 settings node

The project includes 6 example workflow JSON files in the `examples/` directory.

```
├── models_registry.json     # Model registry (7 model definitions)
└── examples/                # 8 example workflows
```

## Supported Models

### Image Generation (900 Nodes)
### Video Generation (901 Nodes)
### Text Understanding (902 Nodes)
### Audio Synthesis (903 Nodes)
### 3D Modeling (904 Nodes)
### Seedance2.0 Assets (905 Nodes)
"""


class RefreshReadmeTests(unittest.TestCase):
    def _counts(self) -> dict[str, int]:
        return {
            "standard": 273,
            "total": 278,
            "examples": 249,
            "seedance_assets": 3,
            "section_image": 59,
            "section_video": 169,
            "section_text": 17,
            "section_audio": 16,
            "section_3d": 12,
        }

    def test_refresh_zh_rewrites_all_targets(self):
        updated = refresh_readme.refresh_zh(ZH_TEMPLATE, self._counts())

        self.assertIn("Nodes-278-blue", updated)
        self.assertIn("本项目当前收录 273 个标准模型 API 节点", updated)
        self.assertIn("总计提供 278 个 ComfyUI 节点", updated)
        self.assertIn("共 278 个 ComfyUI 节点，其中包含 273 个标准模型节点", updated)
        self.assertIn("模型注册表（273 个模型定义）", updated)
        self.assertIn("目录下提供了 249 个示例工作流", updated)
        self.assertIn("└── examples/                # 249 个示例工作流", updated)

        self.assertIn("### 图像生成（59 个节点）", updated)
        self.assertIn("### 视频生成（169 个节点）", updated)
        self.assertIn("### 文本理解（17 个节点）", updated)
        self.assertIn("### 音频合成（16 个节点）", updated)
        self.assertIn("### 3D 建模（12 个节点）", updated)
        self.assertIn("### Seedance2.0 素材资产（3 个节点）", updated)

        # no leftover placeholders
        stale_markers = (
            "Nodes-1-",
            "收录 2 个",
            "提供 3 个 ComfyUI",
            "共 4 个",
            "包含 5 个",
            "提供了 6 个",
            "（7 个",
            "# 8 个",
            "（900 个节点）",
            "（901 个节点）",
            "（902 个节点）",
            "（903 个节点）",
            "（904 个节点）",
            "（905 个节点）",
        )
        for stale in stale_markers:
            self.assertNotIn(stale, updated)

    def test_refresh_en_rewrites_all_targets(self):
        updated = refresh_readme.refresh_en(EN_TEMPLATE, self._counts())

        self.assertIn("Nodes-278-blue", updated)
        self.assertIn("currently includes 273 standard model API nodes", updated)
        self.assertIn("it provides 278 ComfyUI nodes in total", updated)
        self.assertIn("- **Node Count** — 278 ComfyUI nodes in total: 273 standard model nodes", updated)
        self.assertIn("Model registry (273 model definitions)", updated)
        self.assertIn("project includes 249 example workflow JSON files", updated)
        self.assertIn("└── examples/                # 249 example workflows", updated)

        self.assertIn("### Image Generation (59 Nodes)", updated)
        self.assertIn("### Video Generation (169 Nodes)", updated)
        self.assertIn("### Text Understanding (17 Nodes)", updated)
        self.assertIn("### Audio Synthesis (16 Nodes)", updated)
        self.assertIn("### 3D Modeling (12 Nodes)", updated)
        self.assertIn("### Seedance2.0 Assets (3 Nodes)", updated)

    def test_refresh_is_idempotent(self):
        counts = self._counts()
        first = refresh_readme.refresh_zh(ZH_TEMPLATE, counts)
        second = refresh_readme.refresh_zh(first, counts)
        self.assertEqual(first, second)

    def test_refresh_file_noop_when_unchanged(self):
        with TemporaryDirectory() as tmp:
            tmp_path = Path(tmp) / "README.md"
            counts = self._counts()
            target = refresh_readme.refresh_zh(ZH_TEMPLATE, counts)
            tmp_path.write_text(target, encoding="utf-8")
            changed = refresh_readme.refresh_file(tmp_path, refresh_readme.refresh_zh, counts)
            self.assertFalse(changed)
            self.assertEqual(tmp_path.read_text(encoding="utf-8"), target)

    def test_load_counts_uses_registry_length(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            registry = [
                {"id": 1, "output_type": "image", "category": "RunningHub/X"},
                {"id": 2, "output_type": "image", "category": "RunningHub/X"},
                {"id": 3, "output_type": "video", "category": "RunningHub/Kling"},
                {"id": 4, "output_type": "audio", "category": "RunningHub/Audio"},
                {"id": 5, "output_type": "3d", "category": "RunningHub/HiTem3D"},
                {"id": 6, "output_type": "string", "category": "RunningHub/RHArt Text"},
                # string output inside a video family → counts as video
                {"id": 7, "output_type": "string", "category": "RunningHub/Kling"},
            ]
            (root / "models_registry.json").write_text(
                json.dumps(registry), encoding="utf-8"
            )
            examples_dir = root / "examples"
            examples_dir.mkdir()
            for i in range(4):
                (examples_dir / f"wf_{i}.json").write_text("{}", encoding="utf-8")

            counts = refresh_readme.load_counts(root)

            self.assertEqual(counts["standard"], 7)
            self.assertEqual(
                counts["total"],
                7
                + refresh_readme.SEEDANCE_ASSET_NODES
                + refresh_readme.LLM_CHAT_NODES
                + refresh_readme.SETTINGS_NODES,
            )
            self.assertEqual(counts["examples"], 4)
            self.assertEqual(counts["seedance_assets"], refresh_readme.SEEDANCE_ASSET_NODES)

            self.assertEqual(counts["section_image"], 2)
            self.assertEqual(counts["section_video"], 2)
            self.assertEqual(counts["section_audio"], 1)
            self.assertEqual(counts["section_3d"], 1)
            self.assertEqual(counts["section_text"], 1)

    def test_load_counts_raises_when_categorization_mismatches(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            registry = [{"id": 1, "output_type": "unknown_type", "category": ""}]
            # Force summed != standard by monkeypatching categorize_sections
            (root / "models_registry.json").write_text(
                json.dumps(registry), encoding="utf-8"
            )

            original = refresh_readme.categorize_sections
            try:
                refresh_readme.categorize_sections = lambda _: {
                    "image": 0, "video": 0, "audio": 0, "3d": 0, "text": 0
                }
                with self.assertRaisesRegex(RuntimeError, "Section categorization sum"):
                    refresh_readme.load_counts(root)
            finally:
                refresh_readme.categorize_sections = original


if __name__ == "__main__":
    unittest.main()
