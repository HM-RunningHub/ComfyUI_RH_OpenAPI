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
    "RH_SparkVideoAssetCreate": "RH Seedance2.0 Asset/Create",
    "RH_SparkVideoAssetQuery": "RH Seedance2.0 Asset/Query",
    "RH_SparkVideoAssetIdsMerge": "RH Seedance2.0 Asset IDs/Merge",
}


NODE_I18N_DEFINITIONS = [
    {
        "internal_name": "RH_SparkVideoAssetCreate",
        "display_name": "RH Seedance2.0素材/创建",
        "display_name_en": "RH Seedance2.0 Asset/Create",
        "name_cn": "Seedance2.0素材/创建",
        "name_en": "Seedance2.0 Asset Create",
        "category": "RunningHub/Seedance2.0 Assets",
    },
    {
        "internal_name": "RH_SparkVideoAssetQuery",
        "display_name": "RH Seedance2.0素材/查询",
        "display_name_en": "RH Seedance2.0 Asset/Query",
        "name_cn": "Seedance2.0素材/查询",
        "name_en": "Seedance2.0 Asset Query",
        "category": "RunningHub/Seedance2.0 Assets",
    },
    {
        "internal_name": "RH_SparkVideoAssetIdsMerge",
        "display_name": "RH Seedance2.0素材ID/合并",
        "display_name_en": "RH Seedance2.0 Asset IDs/Merge",
        "name_cn": "Seedance2.0素材ID/合并",
        "name_en": "Seedance2.0 Asset IDs Merge",
        "category": "RunningHub/Seedance2.0 Assets",
    },
]
