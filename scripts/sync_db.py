#!/usr/bin/env python3
"""
Sync models_registry.json with RH production database.

Usage (run from project root via D:\\ComfyUI\\python_embeded\\python.exe):
    python scripts/sync_db.py              # diff only — show NEW / MODIFIED / REMOVED
    python scripts/sync_db.py --apply      # diff + write changes to registry
    python scripts/sync_db.py --workflows  # also generate example workflows for new nodes
    python scripts/sync_db.py --apply --workflows   # full update

PowerShell one-liner:
    powershell.exe -NoProfile -Command "cd 'F:\\code\\ComfyUI_RH_OpenAPI'; D:\\ComfyUI\\python_embeded\\python.exe scripts/sync_db.py"
    powershell.exe -NoProfile -Command "cd 'F:\\code\\ComfyUI_RH_OpenAPI'; D:\\ComfyUI\\python_embeded\\python.exe scripts/sync_db.py --apply --workflows"
"""

import argparse
import json
import os
import re
import sys

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

DB_HOST = "10.132.11.32"
DB_PORT = 3306
DB_USER = "rhuser"
DB_PASS = "8jgU0X6pPw"
DB_NAME = "rh_prod"

SKIP_KEYWORDS = ["test", "\u5e9f\u5f03", "delete", "\u4e34\u65f6", "\u526f\u672c", "Copy"]

CATEGORY_MAP = {
    "rhart-image-n": "RunningHub/RHArt Image",
    "rhart-image-g": "RunningHub/RHArt Image",
    "rhart-image-v": "RunningHub/RHArt Image",
    "rhart-image-qwen": "RunningHub/RHArt Image Qwen",
    "rhart-video-g": "RunningHub/RHArt Video G",
    "rhart-video-s": "RunningHub/RHArt Video",
    "rhart-video-v3": "RunningHub/RHArt Video",
    "rhart-video": "RunningHub/RHArt Video",
    "rhart-minimax": "RunningHub/RHArt Video",
    "rhart-text": "RunningHub/RHArt Text",
    "rhart-audio": "RunningHub/RHArt Audio",
    "kling": "RunningHub/Kling",
    "minimax": "RunningHub/MiniMax",
    "seedream": "RunningHub/Seedream",
    "seedance": "RunningHub/Seedance",
    "alibaba": "RunningHub/Alibaba",
    "vidu": "RunningHub/Vidu",
    "youchuan": "RunningHub/Midjourney",
    "hunyuan3d": "RunningHub/Hunyuan3D",
    "hitem3d": "RunningHub/HiTem3D",
    "topazlabs": "RunningHub/TopazLabs",
}

# Sorted by key length desc for correct prefix matching
_SORTED_PREFIXES = sorted(CATEGORY_MAP.keys(), key=len, reverse=True)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def ep_to_class_name(endpoint: str) -> str:
    parts = re.split(r"[/\-_.]", endpoint)
    return "".join(p.capitalize() for p in parts if p)


def determine_output_type(endpoint: str, name: str) -> str:
    ep = endpoint.lower()
    n = name.lower()
    if any(k in ep for k in ["3d", "hunyuan3d"]):
        return "3d"
    if any(k in ep for k in ["audio", "speech", "music", "voice"]):
        return "audio"
    if "text-to-text" in ep or "image-to-text" in ep or "video-to-text" in ep:
        return "string"
    if any(k in ep or k in n for k in ["video", "i2v", "t2v"]):
        return "video"
    if "video-upscale" in ep:
        return "video"
    if "motion-control" in ep or "elements" in ep:
        return "video"
    if any(k in ep for k in ["image", "upscale", "edit", "text-to-image"]):
        return "image"
    return "string"


def determine_category(endpoint: str) -> str:
    for prefix in _SORTED_PREFIXES:
        if endpoint.startswith(prefix):
            return CATEGORY_MAP[prefix]
    return "RunningHub/Other"


def should_skip(ep: str, name: str, input_config_json) -> bool:
    combined = (ep + name).lower()
    for kw in SKIP_KEYWORDS:
        if kw.lower() in combined:
            return True
    if input_config_json:
        try:
            params = json.loads(input_config_json) if isinstance(input_config_json, str) else input_config_json
            if any("##" in (p.get("fieldKey", "") or "") for p in params):
                return True
        except (json.JSONDecodeError, TypeError):
            pass
    return False


def parse_params(input_config_json) -> list:
    if not input_config_json:
        return []
    params_raw = json.loads(input_config_json) if isinstance(input_config_json, str) else input_config_json
    params = []
    for p in params_raw:
        fk = p.get("fieldKey", "") or ""
        if "##" in fk:
            continue
        ptype = p.get("type", "STRING")
        if ptype == "COMPLEX":
            continue

        param = {
            "fieldKey": fk,
            "type": ptype,
            "required": bool(p.get("required", False)),
            "label": p.get("title") or fk,
            "description": p.get("paramDesc") or fk,
        }

        # defaultValue — skip for media types (long URLs)
        if ptype not in ("IMAGE", "VIDEO", "AUDIO"):
            dv = p.get("defaultValue")
            if dv is not None and dv != "":
                if ptype == "INT":
                    try:
                        dv = int(dv)
                    except (ValueError, TypeError):
                        pass
                elif ptype == "FLOAT":
                    try:
                        dv = float(dv)
                    except (ValueError, TypeError):
                        pass
                elif ptype == "BOOLEAN":
                    if isinstance(dv, str):
                        dv = dv.lower() in ("true", "1", "yes")
                param["defaultValue"] = dv

        if p.get("options"):
            param["options"] = p["options"]
        if p.get("multipleInputs"):
            param["multipleInputs"] = p["multipleInputs"]
        # DB has typo "maxInpuNum"
        max_input = p.get("maxInputNum") or p.get("maxInpuNum")
        if max_input:
            param["maxInputNum"] = max_input
        for extra in ("maxLength", "accept", "maxSize"):
            if p.get(extra) is not None:
                param[extra] = p[extra]
        for extra in ("min", "max", "step"):
            if p.get(extra) is not None:
                param[extra] = p[extra]
        params.append(param)
    return params


def build_entry(api: dict) -> dict:
    ep = api["_ep"]
    class_name = ep_to_class_name(ep)
    return {
        "class_name": class_name,
        "internal_name": f"RH_{class_name}",
        "display_name": f"RH {api['name']}",
        "name_cn": api["name"],
        "name_en": api.get("name_en", "") or ep,
        "endpoint": ep,
        "output_type": determine_output_type(ep, api["name"]),
        "category": determine_category(ep),
        "params": parse_params(api.get("input_config_json")),
    }


# ---------------------------------------------------------------------------
# Workflow generator
# ---------------------------------------------------------------------------

def generate_workflow(node_type, display_name, endpoint, output_type, media_inputs, optional_media):
    """Generate a ComfyUI example workflow JSON dict."""
    node_id = 1
    link_id = 1
    nodes, links = [], []
    all_media = media_inputs + optional_media

    # Settings node
    nodes.append({
        "id": node_id, "type": "RHSettingsNode",
        "pos": [50, 100], "size": [330, 82],
        "flags": {}, "order": 0, "mode": 0, "inputs": [],
        "outputs": [{"name": "api_config", "type": "RH_OPENAPI_CONFIG", "links": [link_id], "slot_index": 0}],
        "properties": {"Node name for S&R": "RHSettingsNode"},
        "widgets_values": ["https://www.runninghub.cn/openapi/v2", "YOUR_API_KEY"],
    })
    settings_id, api_config_link = node_id, link_id
    node_id += 1
    link_id += 1

    # API node
    api_inputs = [{"name": m["name"], "type": m["type"], "link": None} for m in all_media]
    api_inputs.append({"name": "api_config", "type": "RH_OPENAPI_CONFIG", "link": api_config_link})

    primary_out = {"name": "video" if output_type == "video" else ("image" if output_type == "image" else "result"),
                   "type": "VIDEO" if output_type == "video" else ("IMAGE" if output_type == "image" else "STRING"),
                   "links": [link_id] if output_type in ("video", "image") else [], "slot_index": 0}
    save_link = link_id
    link_id += 1

    nodes.append({
        "id": node_id, "type": node_type,
        "pos": [500, 100], "size": [350, 300],
        "flags": {}, "order": 1, "mode": 0,
        "inputs": api_inputs,
        "outputs": [primary_out,
                    {"name": "url", "type": "STRING", "links": [], "slot_index": 1},
                    {"name": "response", "type": "STRING", "links": [], "slot_index": 2}],
        "properties": {"Node name for S&R": node_type},
        "widgets_values": [], "title": display_name,
    })
    api_id = node_id
    node_id += 1
    links.append([api_config_link, settings_id, 0, api_id, len(all_media), "RH_OPENAPI_CONFIG"])

    # Note
    media_text = ""
    if all_media:
        media_text = "\n\nMedia inputs (connect as needed):\n" + "\n".join(f"  - {m['name']} ({m['type']})" for m in all_media)
    note = f"Example: {display_name}\nEndpoint: /{endpoint}\nOutput: {output_type}\n\nSteps:\n1. Set API Key in Settings node\n2. Adjust parameters and Queue Prompt{media_text}"
    nodes.append({
        "id": node_id, "type": "Note", "pos": [50, -100], "size": [420, 240],
        "flags": {}, "order": 3, "mode": 0, "inputs": [], "outputs": [],
        "properties": {"text": note}, "widgets_values": [note], "color": "#432", "bgcolor": "#653",
    })
    node_id += 1

    # Save node
    if output_type in ("video", "image"):
        stype = "SaveVideo" if output_type == "video" else "SaveImage"
        iname = "video" if output_type == "video" else "images"
        itype = "VIDEO" if output_type == "video" else "IMAGE"
        nodes.append({
            "id": node_id, "type": stype, "pos": [900, 100], "size": [300, 200],
            "flags": {}, "order": 2, "mode": 0,
            "inputs": [{"name": iname, "type": itype, "link": save_link}],
            "outputs": [], "properties": {"Node name for S&R": stype}, "widgets_values": ["RH_"],
        })
        links.append([save_link, api_id, 0, node_id, 0, itype])
        node_id += 1

    return {
        "last_node_id": node_id - 1, "last_link_id": link_id - 1,
        "nodes": nodes, "links": links, "groups": [], "config": {},
        "extra": {"ds": {"scale": 1, "offset": [0, 0]}}, "version": 0.4,
    }


def media_inputs_from_params(params: list):
    """Extract media input info from parsed params for workflow generation."""
    required, optional = [], []
    for p in params:
        if p["type"] in ("IMAGE", "VIDEO", "AUDIO"):
            is_multiple = p.get("multipleInputs", False)
            max_num = p.get("maxInputNum", 1) or 1
            base = re.sub(r"Url$|Urls$", "", p["fieldKey"])
            base = re.sub(r"([A-Z])", r"_\1", base).lower().strip("_")
            if base == "videos":
                base = "video"

            if is_multiple and max_num > 1:
                for i in range(1, max_num + 1):
                    entry = {"name": f"{base}{i}", "type": p["type"]}
                    if i == 1 and p.get("required"):
                        required.append(entry)
                    else:
                        optional.append(entry)
            else:
                entry = {"name": base, "type": p["type"]}
                if p.get("required"):
                    required.append(entry)
                else:
                    optional.append(entry)
    return required, optional


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Sync models_registry.json with RH production DB")
    parser.add_argument("--apply", action="store_true", help="Write changes to registry (default: diff only)")
    parser.add_argument("--workflows", action="store_true", help="Generate example workflows for new nodes")
    args = parser.parse_args()

    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    registry_path = os.path.join(project_root, "models_registry.json")

    # --- Load registry ---
    with open(registry_path, "r", encoding="utf-8") as f:
        registry = json.load(f)
    reg_by_ep = {m["endpoint"].lstrip("/"): m for m in registry}
    print(f"Registry: {len(registry)} entries")

    # --- Query DB ---
    import pymysql
    conn = pymysql.connect(host=DB_HOST, port=DB_PORT, user=DB_USER,
                           password=DB_PASS, database=DB_NAME, charset="utf8mb4")
    cursor = conn.cursor(pymysql.cursors.DictCursor)
    cursor.execute(
        "SELECT id, name, name_en, rh_endpoint, input_config_json, status "
        "FROM t_api_sku WHERE category_type='STANDARD_MODEL' AND del_flag=0 ORDER BY id"
    )
    db_apis = cursor.fetchall()
    conn.close()

    for a in db_apis:
        a["_ep"] = (a["rh_endpoint"] or "").lstrip("/")
    print(f"Database: {len(db_apis)} STANDARD_MODEL entries")
    print()

    # --- Diff: NEW ---
    new_apis = []
    for a in db_apis:
        if not a["_ep"] or a["_ep"] in reg_by_ep:
            continue
        if should_skip(a["_ep"], a["name"], a.get("input_config_json")):
            continue
        new_apis.append(a)

    print(f"NEW (in DB, not in registry): {len(new_apis)}")
    for a in new_apis:
        entry = build_entry(a)
        print(f"  [{a['status']}] {a['_ep']}  →  {entry['internal_name']}  output={entry['output_type']}  cat={entry['category']}  params={len(entry['params'])}")

    # --- Diff: REMOVED ---
    db_eps = {a["_ep"] for a in db_apis if a["_ep"]}
    removed = [ep for ep in reg_by_ep if ep not in db_eps]
    print(f"\nREMOVED (in registry, not in DB): {len(removed)}")
    for ep in removed:
        print(f"  {ep}")

    # --- Diff: MODIFIED (param key diff) ---
    modified = []
    for a in db_apis:
        ep = a["_ep"]
        if not ep or ep not in reg_by_ep:
            continue
        if should_skip(ep, a["name"], a.get("input_config_json")):
            continue
        reg_entry = reg_by_ep[ep]
        new_params = parse_params(a.get("input_config_json"))
        new_keys = {p["fieldKey"] for p in new_params}
        old_keys = {p["fieldKey"] for p in reg_entry.get("params", [])}
        if new_keys != old_keys:
            modified.append({"ep": ep, "name": a["name"], "api": a,
                             "added": new_keys - old_keys, "removed": old_keys - new_keys,
                             "new_params": new_params})

    print(f"\nMODIFIED (param key changes): {len(modified)}")
    for m in modified:
        print(f"  {m['ep']}")
        if m["added"]:
            print(f"    +params: {m['added']}")
        if m["removed"]:
            print(f"    -params: {m['removed']}")

    # --- Summary ---
    total_changes = len(new_apis) + len(removed) + len(modified)
    if total_changes == 0:
        print("\n✅ Registry is up to date. No changes needed.")
        return

    if not args.apply:
        print(f"\n⚠️  {total_changes} change(s) found. Run with --apply to update registry.")
        return

    # --- Apply: add new entries ---
    added_count = 0
    new_entries = []
    for a in new_apis:
        entry = build_entry(a)
        registry.append(entry)
        new_entries.append(entry)
        added_count += 1
        print(f"\n  ADDED: {entry['endpoint']} → {entry['internal_name']}")

    # --- Apply: update modified params ---
    updated_count = 0
    for m in modified:
        reg_entry = reg_by_ep[m["ep"]]
        reg_entry["params"] = m["new_params"]
        updated_count += 1
        print(f"  UPDATED params: {m['ep']}")

    # --- Verify no duplicates ---
    names = [e["internal_name"] for e in registry]
    eps = [e["endpoint"] for e in registry]
    dup_n = {n for n in names if names.count(n) > 1}
    dup_e = {e for e in eps if eps.count(e) > 1}
    if dup_n:
        print(f"\n⚠️  Duplicate internal_names: {dup_n}")
    if dup_e:
        print(f"⚠️  Duplicate endpoints: {dup_e}")

    # --- Write registry ---
    with open(registry_path, "w", encoding="utf-8") as f:
        json.dump(registry, f, ensure_ascii=False, indent=2)
    print(f"\n✅ Registry saved: {len(registry)} entries (+{added_count} new, ~{updated_count} updated)")

    # --- Generate workflows ---
    if args.workflows and new_entries:
        print(f"\nGenerating {len(new_entries)} example workflows...")
        examples_dir = os.path.join(project_root, "examples")
        for entry in new_entries:
            cat_folder = entry["category"].replace("RunningHub/", "").replace(" ", "_").replace("/", "_")
            out_dir = os.path.join(examples_dir, cat_folder)
            os.makedirs(out_dir, exist_ok=True)

            req_media, opt_media = media_inputs_from_params(entry["params"])
            wf = generate_workflow(
                entry["internal_name"], entry["display_name"],
                entry["endpoint"], entry["output_type"],
                req_media, opt_media,
            )
            filename = entry["endpoint"].replace("/", "_").replace(".", "_") + ".json"
            filepath = os.path.join(out_dir, filename)
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(wf, f, ensure_ascii=False, indent=2)
            print(f"  → {os.path.relpath(filepath, project_root)}")

    print("\nDone.")


if __name__ == "__main__":
    main()
