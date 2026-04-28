"""Build public AI integration registry and capability docs.

This script converts the internal project model registry into files that are
safe and useful for third-party developers and AI coding agents.
"""

from __future__ import annotations

import json
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional


ROOT = Path(__file__).resolve().parents[2]
KIT_ROOT = ROOT / "developer-kit"
SOURCE_REGISTRY = ROOT / "models_registry.json"
PUBLIC_REGISTRY = KIT_ROOT / "model-registry.public.json"
PUBLIC_PRICING = KIT_ROOT / "pricing.public.json"
CAPABILITIES_DOC = KIT_ROOT / "capabilities.md"

REGISTRY_VERSION = "public-2026-04-29"
FORBIDDEN_MODEL_KEYS = {
    "internal_name",
    "price_badge",
    "price_badge_meta",
    "billing",
    "billing_spec",
}
PUBLIC_MODEL_KEYS = {
    "class_name",
    "display_name",
    "name_cn",
    "name_en",
    "endpoint",
    "output_type",
    "category",
    "params",
    "asset_ids_mode",
    "real_person_asset_slots",
    "real_person_mode_default",
}


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, data: Any) -> None:
    path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def sanitize_param(param: Mapping[str, Any]) -> Dict[str, Any]:
    allowed_keys = {
        "fieldKey",
        "type",
        "required",
        "label",
        "description",
        "descriptionEn",
        "defaultValue",
        "options",
        "multipleInputs",
        "maxInputNum",
        "maxInpuNum",
        "accept",
        "maxSize",
        "min",
        "max",
        "step",
        "maxLength",
        "tail_insert",
    }
    result = {key: param[key] for key in allowed_keys if key in param}
    if "options" in result and isinstance(result["options"], list):
        result["options"] = [sanitize_option(option) for option in result["options"]]
    return result


def sanitize_option(option: Any) -> Any:
    if not isinstance(option, Mapping):
        return option
    allowed = {"value", "description", "descriptionEn"}
    return {key: option[key] for key in allowed if key in option}


def sanitize_model(model: Mapping[str, Any]) -> Dict[str, Any]:
    result = {key: model[key] for key in PUBLIC_MODEL_KEYS if key in model}
    result["params"] = [sanitize_param(param) for param in model.get("params", [])]
    for key in FORBIDDEN_MODEL_KEYS:
        result.pop(key, None)
    return result


def build_public_registry(models: Iterable[Mapping[str, Any]]) -> Dict[str, Any]:
    public_models = [sanitize_model(model) for model in models]
    public_models.sort(key=lambda item: (str(item.get("output_type", "")), str(item.get("endpoint", ""))))
    counts_by_output_type = Counter(str(model.get("output_type") or "unknown") for model in public_models)
    counts_by_category = Counter(str(model.get("category") or "Uncategorized") for model in public_models)

    return {
        "version": REGISTRY_VERSION,
        "source": "models_registry.json",
        "model_count": len(public_models),
        "counts_by_output_type": dict(sorted(counts_by_output_type.items())),
        "counts_by_category": dict(sorted(counts_by_category.items())),
        "models": public_models,
    }


def extract_depends_on(price_badge: Mapping[str, Any]) -> List[str]:
    depends_on = price_badge.get("depends_on") or {}
    widgets = depends_on.get("widgets") or []
    names = []
    for widget in widgets:
        if isinstance(widget, Mapping) and widget.get("name"):
            names.append(str(widget["name"]))
    return names


def extract_suffix(expr: str) -> str:
    match = re.search(r'"suffix"\s*:\s*"([^"]+)"', expr)
    return match.group(1) if match else "/次"


def parse_fixed_cny(expr: str) -> Optional[float]:
    match = re.search(r'"cny"\s*:\s*\$round\(\s*([0-9]+(?:\.[0-9]+)?)\s*,\s*4\s*\)', expr)
    if not match:
        match = re.search(r'"cny"\s*:\s*([0-9]+(?:\.[0-9]+)?)', expr)
    return float(match.group(1)) if match else None


def parse_price_table(expr: str) -> Optional[Dict[str, str]]:
    match = re.search(r"\$table\s*:=\s*(\{.*?\})\s*;", expr, flags=re.DOTALL)
    if not match:
        return None
    try:
        table = json.loads(match.group(1))
    except json.JSONDecodeError:
        return None
    if not isinstance(table, dict):
        return None
    return {str(key): str(value) for key, value in table.items()}


def build_pricing_rule(table_key: str, value: str, depends_on: List[str]) -> Dict[str, Any]:
    parts = table_key.split("|")
    when = {}
    for index, field in enumerate(depends_on):
        if index < len(parts):
            when[field] = parts[index]
    if not when and len(depends_on) == 1:
        when[depends_on[0]] = table_key
    return {
        "when": when,
        "price": round(float(value), 4),
    }


def public_pricing_for_model(model: Mapping[str, Any]) -> Optional[Dict[str, Any]]:
    price_badge = model.get("price_badge")
    if not isinstance(price_badge, Mapping):
        return None

    expr = str(price_badge.get("expr") or "")
    endpoint = str(model.get("endpoint") or "")
    if not expr or not endpoint:
        return None

    depends_on = extract_depends_on(price_badge)
    suffix = extract_suffix(expr)
    base = {
        "endpoint": endpoint,
        "name_cn": model.get("name_cn") or model.get("display_name") or "",
        "name_en": model.get("name_en") or "",
        "currency": "CNY",
        "unit": suffix,
        "source": "derived_from_public_safe_pricing_summary",
        "updated_at": "2026-04-29",
    }

    table = parse_price_table(expr)
    if table and depends_on:
        rules = [build_pricing_rule(key, value, depends_on) for key, value in sorted(table.items())]
        return {
            **base,
            "pricing_type": "parameter_based",
            "depends_on": depends_on,
            "rules": rules,
        }

    fixed = parse_fixed_cny(expr)
    if fixed is not None:
        return {
            **base,
            "pricing_type": "fixed",
            "price": round(fixed, 4),
        }

    return {
        **base,
        "pricing_type": "unparsed",
        "note": "Pricing exists but could not be converted to public structured rules. Check official pricing before quoting costs.",
    }


def build_public_pricing(models: Iterable[Mapping[str, Any]]) -> Dict[str, Any]:
    model_list = list(models)
    entries = [entry for model in model_list if (entry := public_pricing_for_model(model))]
    if not entries and PUBLIC_PRICING.exists():
        endpoint_set = {str(model.get("endpoint")) for model in model_list if model.get("endpoint")}
        existing = read_json(PUBLIC_PRICING)
        entries = [
            entry
            for entry in existing.get("pricing", [])
            if isinstance(entry, Mapping) and str(entry.get("endpoint")) in endpoint_set
        ]
    entries.sort(key=lambda item: str(item.get("endpoint", "")))
    counts = Counter(str(entry.get("pricing_type") or "unknown") for entry in entries)
    return {
        "version": REGISTRY_VERSION,
        "source": "models_registry.json public-safe pricing summaries",
        "note": (
            "Public-safe pricing summary for AI-assisted integration. Prices may change; "
            "check official RunningHub pricing before showing final costs to end users."
        ),
        "pricing_count": len(entries),
        "counts_by_pricing_type": dict(sorted(counts.items())),
        "pricing": entries,
    }


def pricing_summary(entry: Optional[Mapping[str, Any]]) -> str:
    if not entry:
        return ""
    unit = str(entry.get("unit") or "")
    if entry.get("pricing_type") == "fixed":
        return f"{entry.get('price')} CNY{unit}"
    if entry.get("pricing_type") == "parameter_based":
        rules = entry.get("rules") or []
        prices = sorted({float(rule["price"]) for rule in rules if "price" in rule})
        depends_on = ",".join(str(item) for item in entry.get("depends_on") or [])
        if not prices:
            return f"parameter-based ({depends_on})"
        if len(prices) == 1:
            return f"{prices[0]:g} CNY{unit} by {depends_on}"
        return f"{prices[0]:g}-{prices[-1]:g} CNY{unit} by {depends_on}"
    return "pricing available; see pricing.public.json"


def model_input_summary(model: Mapping[str, Any]) -> str:
    chunks = []
    for param in model.get("params", []):
        field = param.get("fieldKey", "")
        ptype = param.get("type", "")
        required = "required" if param.get("required") else "optional"
        if field and ptype:
            chunks.append(f"{field}:{ptype}:{required}")
    return ", ".join(chunks)


def build_capabilities_doc(registry: Mapping[str, Any], pricing: Mapping[str, Any]) -> str:
    models = list(registry["models"])
    pricing_by_endpoint = {
        str(entry.get("endpoint")): entry
        for entry in pricing.get("pricing", [])
        if entry.get("endpoint")
    }
    by_output_type: Dict[str, List[Mapping[str, Any]]] = defaultdict(list)
    for model in models:
        by_output_type[str(model.get("output_type") or "unknown")].append(model)

    lines = [
        "# RunningHub API Capabilities",
        "",
        "This file is generated from `model-registry.public.json`.",
        "Pricing summaries are generated from `pricing.public.json` when available.",
        "It gives developers and AI coding agents a fast index of available model capabilities.",
        "",
        "## Summary",
        "",
        f"- Total models: {registry['model_count']}",
    ]

    for output_type, count in registry["counts_by_output_type"].items():
        lines.append(f"- `{output_type}` outputs: {count}")

    lines.extend(
        [
            "",
            "## How To Use This File With AI",
            "",
            "Ask the AI agent to use this file to choose candidate endpoints, then use",
            "`model-registry.public.json` as the source of truth for exact parameters.",
            "Use `pricing.public.json` for cost-aware choices, but verify official",
            "RunningHub pricing before showing final costs to end users.",
            "The AI must not infer enum values or required fields from this summary.",
            "",
        ]
    )

    for output_type in sorted(by_output_type):
        entries = sorted(by_output_type[output_type], key=lambda item: str(item.get("endpoint", "")))
        lines.extend([f"## {output_type.title()} Models", ""])
        lines.append("| Endpoint | Name | Inputs | Pricing |")
        lines.append("| --- | --- | --- | --- |")
        for model in entries:
            endpoint = model.get("endpoint", "")
            name = model.get("name_en") or model.get("name_cn") or model.get("display_name") or ""
            inputs = model_input_summary(model)
            price = pricing_summary(pricing_by_endpoint.get(str(endpoint)))
            lines.append(
                f"| `{endpoint}` | {escape_table(str(name))} | "
                f"{escape_table(inputs)} | {escape_table(price)} |"
            )
        lines.append("")

    return "\n".join(lines)


def escape_table(text: str) -> str:
    return text.replace("|", "\\|").replace("\n", " ")


def assert_public_safe(registry: Mapping[str, Any]) -> None:
    forbidden_hits = []
    for idx, model in enumerate(registry.get("models", [])):
        for key in FORBIDDEN_MODEL_KEYS:
            if key in model:
                forbidden_hits.append(f"models[{idx}].{key}")
    if forbidden_hits:
        raise RuntimeError(f"Forbidden keys in public registry: {', '.join(forbidden_hits[:20])}")


def assert_pricing_public_safe(pricing: Mapping[str, Any]) -> None:
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
    hits = [term for term in forbidden_terms if term in serialized]
    if hits:
        raise RuntimeError(f"Forbidden internal pricing terms in public pricing: {', '.join(hits)}")


def main() -> None:
    source_models = read_json(SOURCE_REGISTRY)
    registry = build_public_registry(source_models)
    pricing = build_public_pricing(source_models)
    assert_public_safe(registry)
    assert_pricing_public_safe(pricing)
    write_json(PUBLIC_REGISTRY, registry)
    write_json(PUBLIC_PRICING, pricing)
    CAPABILITIES_DOC.write_text(build_capabilities_doc(registry, pricing) + "\n", encoding="utf-8")
    print(f"Wrote {PUBLIC_REGISTRY} ({registry['model_count']} models)")
    print(f"Wrote {PUBLIC_PRICING} ({pricing['pricing_count']} pricing entries)")
    print(f"Wrote {CAPABILITIES_DOC}")


if __name__ == "__main__":
    main()
