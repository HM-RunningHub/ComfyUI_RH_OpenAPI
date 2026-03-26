"""
SparkVideo asset management node exports.
"""

from .asset_nodes import (
    RH_SparkVideoAssetCreate,
    RH_SparkVideoAssetIdsMerge,
    RH_SparkVideoAssetQuery,
)


NODE_CLASS_MAPPINGS = {
    "RH_SparkVideoAssetCreate": RH_SparkVideoAssetCreate,
    "RH_SparkVideoAssetQuery": RH_SparkVideoAssetQuery,
    "RH_SparkVideoAssetIdsMerge": RH_SparkVideoAssetIdsMerge,
}


NODE_DISPLAY_NAME_MAPPINGS = {
    "RH_SparkVideoAssetCreate": "RH SparkVideo 素材/创建",
    "RH_SparkVideoAssetQuery": "RH SparkVideo 素材/查询",
    "RH_SparkVideoAssetIdsMerge": "RH SparkVideo 素材ID/合并",
}


NODE_I18N_DEFINITIONS = [
    {
        "internal_name": "RH_SparkVideoAssetCreate",
        "display_name": "RH SparkVideo 素材/创建",
        "display_name_en": "RH SparkVideo Asset/Create",
        "name_cn": "SparkVideo 素材/创建",
        "name_en": "SparkVideo Asset Create",
        "category": "RunningHub/SparkVideo Assets",
    },
    {
        "internal_name": "RH_SparkVideoAssetQuery",
        "display_name": "RH SparkVideo 素材/查询",
        "display_name_en": "RH SparkVideo Asset/Query",
        "name_cn": "SparkVideo 素材/查询",
        "name_en": "SparkVideo Asset Query",
        "category": "RunningHub/SparkVideo Assets",
    },
    {
        "internal_name": "RH_SparkVideoAssetIdsMerge",
        "display_name": "RH SparkVideo 素材ID/合并",
        "display_name_en": "RH SparkVideo Asset IDs/Merge",
        "name_cn": "SparkVideo 素材ID/合并",
        "name_en": "SparkVideo Asset IDs Merge",
        "category": "RunningHub/SparkVideo Assets",
    },
]
