"""
ComfyUI_RH_OpenAPI - RunningHub OpenAPI standard model nodes.

Provides 110+ API nodes for RunningHub's standard model endpoints,
covering image generation, video generation, audio synthesis, and 3D modeling.
"""

import json
import os
import re

from .nodes.settings_node import RHSettingsNode
from .nodes.node_factory import create_all_nodes

_class_mappings, _display_mappings = create_all_nodes()

NODE_CLASS_MAPPINGS = {
    "RHSettingsNode": RHSettingsNode,
    **_class_mappings,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "RHSettingsNode": "RH OpenAPI Settings",
    **_display_mappings,
}

WEB_DIRECTORY = "./web"

# ---------------------------------------------------------------------------
# Auto-generate i18n files from models_registry.json
# ---------------------------------------------------------------------------

_UPPER_WORDS = {
    "hd", "cgi", "3d", "ai", "gpt", "xai", "q2", "q3",
    "pro", "std", "v1", "v2", "v3", "v4", "v5", "v6", "v7",
    "i2v", "t2v",
}
_LOWER_WORDS = {"to", "of", "and", "the", "a"}

_CATEGORY_NAME_EN = {
    "RHArt Image": "🖼️ RHArt Image",
    "RHArt Video": "🎬 RHArt Video",
    "RHArt Video G": "🎥 RHArt Video G",
    "RHArt Text": "📝 RHArt Text",
    "Kling": "🎞️ Kling",
    "Vidu": "📹 Vidu",
    "Wan": "🌀 Wan",
    "MiniMax": "🐚 MiniMax",
    "Seedream": "🌱 Seedream",
    "Seedance": "💃 Seedance",
    "Youchuan": "🚢 Midjourney",
    "Audio": "🎵 Audio",
    "Hunyuan3D": "🧊 Hunyuan 3D",
    "HiTem3D": "🔷 HiTem 3D",
    "TopazLabs": "💎 Topaz Labs",
    "RHArt Image Qwen": "🤖 RHArt Image Qwen",
    "Alibaba": "🎨 Alibaba Qwen",
}

_CATEGORY_NAME_ZH = {
    "RHArt Image": "🖼️ RH 全能图像",
    "RHArt Video": "🎬 RH 全能视频",
    "RHArt Video G": "🎥 RH 全能视频G",
    "RHArt Text": "📝 RH 多模态文本",
    "Kling": "🎞️ 可灵 Kling",
    "Vidu": "📹 生数 Vidu",
    "Wan": "🌀 通义万相 Wan",
    "MiniMax": "🐚 MiniMax 海螺",
    "Seedream": "🌱 Seedream 图像",
    "Seedance": "💃 Seedance 视频",
    "Youchuan": "🚢 有船 Midjourney",
    "Audio": "🎵 音频生成",
    "Hunyuan3D": "🧊 混元 3D",
    "HiTem3D": "🔷 HiTem 3D",
    "TopazLabs": "💎 Topaz Labs",
    "RHArt Image Qwen": "🤖 RHArt 图像 Qwen",
    "Alibaba": "🎨 阿里 通义万相 Qwen",
}


def _name_en_to_display(name_en: str) -> str:
    """Convert endpoint-style name_en to a readable English display name."""
    words = re.split(r"[-/\s]+", name_en)
    result = []
    for w in words:
        if not w:
            continue
        wl = w.lower()
        if wl in _UPPER_WORDS:
            result.append(w.upper())
        elif wl in _LOWER_WORDS and result:
            result.append(wl)
        elif re.match(r"^v\d", wl):
            result.append("V" + w[1:])
        else:
            result.append(w.capitalize())
    return " ".join(result)


def _generate_i18n_files():
    """Generate ComfyUI locales/ and panel_i18n.json from models_registry.json."""
    base_dir = os.path.dirname(__file__)
    registry_path = os.path.join(base_dir, "models_registry.json")

    try:
        with open(registry_path, "r", encoding="utf-8") as f:
            registry = json.load(f)
    except Exception:
        return

    # Build nodeDefs for en and zh
    node_defs_en = {}
    node_defs_zh = {}
    panel_nodes_en = {}
    panel_nodes_zh = {}

    for m in registry:
        iname = m.get("internal_name", "")
        name_cn = m.get("name_cn", "")
        name_en = m.get("name_en", "")
        display_cn = m.get("display_name", "")
        endpoint = m.get("endpoint", "")

        en_source = name_en.strip() or endpoint
        en_display = ("RH " + _name_en_to_display(en_source)) if en_source else iname
        zh_display = display_cn or ("RH " + name_cn if name_cn else iname)

        node_defs_en[iname] = {"display_name": en_display}
        node_defs_zh[iname] = {"display_name": zh_display}
        panel_nodes_en[iname] = en_display
        panel_nodes_zh[iname] = zh_display

    # Settings node
    node_defs_en["RHSettingsNode"] = {"display_name": "RH OpenAPI Settings"}
    node_defs_zh["RHSettingsNode"] = {"display_name": "RH OpenAPI 设置"}
    panel_nodes_en["RHSettingsNode"] = "RH OpenAPI Settings"
    panel_nodes_zh["RHSettingsNode"] = "RH OpenAPI 设置"

    # Write locales/en/ and locales/zh/
    for lang, nd in [("en", node_defs_en), ("zh", node_defs_zh)]:
        lang_dir = os.path.join(base_dir, "locales", lang)
        os.makedirs(lang_dir, exist_ok=True)

        with open(os.path.join(lang_dir, "nodeDefs.json"), "w", encoding="utf-8") as f:
            json.dump(nd, f, ensure_ascii=False, indent=2)

    # Write locales main.json (category translations)
    categories = sorted(set(
        m.get("category", "").replace("RunningHub/", "")
        for m in registry if m.get("category")
    ))

    en_cats = {"RunningHub": "RunningHub"}
    zh_cats = {"RunningHub": "RunningHub"}
    for cat in categories:
        en_val = _CATEGORY_NAME_EN.get(cat, cat)
        zh_val = _CATEGORY_NAME_ZH.get(cat, cat)
        en_cats[cat] = re.sub(r"^[^\w]+", "", en_val).strip() if en_val else cat
        zh_cats[cat] = re.sub(r"^[^\u4e00-\u9fffA-Za-z]+", "", zh_val).strip() if zh_val else cat

    for lang, cats in [("en", en_cats), ("zh", zh_cats)]:
        lang_dir = os.path.join(base_dir, "locales", lang)
        with open(os.path.join(lang_dir, "main.json"), "w", encoding="utf-8") as f:
            json.dump({"nodeCategories": cats}, f, ensure_ascii=False, indent=2)

    # Write web/js/panel_i18n.json for rh_panel.js
    panel_i18n = {
        "categories": {
            "zh": _CATEGORY_NAME_ZH,
            "en": _CATEGORY_NAME_EN,
        },
        "nodes": {
            "zh": panel_nodes_zh,
            "en": panel_nodes_en,
        },
        "ui": {
            "zh": {
                "search_placeholder": "🔍 搜索节点...",
                "stats": "共 {categories} 个分类，{nodes} 个节点 | Ctrl+Shift+R",
                "no_results": "😕 未找到匹配的节点",
                "tooltip": "RunningHub 节点面板 (Ctrl+Shift+R)",
            },
            "en": {
                "search_placeholder": "🔍 Search nodes...",
                "stats": "{categories} categories, {nodes} nodes | Ctrl+Shift+R",
                "no_results": "😕 No matching nodes found",
                "tooltip": "RunningHub Node Panel (Ctrl+Shift+R)",
            },
        },
    }

    panel_path = os.path.join(base_dir, "web", "js", "panel_i18n.json")
    try:
        with open(panel_path, "w", encoding="utf-8") as f:
            json.dump(panel_i18n, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


_node_list_path = os.path.join(os.path.dirname(__file__), "web", "js", "node_list.json")
try:
    with open(_node_list_path, "w", encoding="utf-8") as f:
        json.dump(sorted(NODE_CLASS_MAPPINGS.keys()), f)
except Exception:
    pass

_generate_i18n_files()

__all__ = ["NODE_CLASS_MAPPINGS", "NODE_DISPLAY_NAME_MAPPINGS", "WEB_DIRECTORY"]
