# ComfyUI_RH_OpenAPI

![License](https://img.shields.io/badge/License-Apache%202.0-green)
![Nodes](https://img.shields.io/badge/Nodes-242-blue)
![ComfyUI](https://img.shields.io/badge/ComfyUI-Custom%20Node-orange)

**English** | [中文](README.md)

**ComfyUI_RH_OpenAPI** is a **1:1 ComfyUI implementation** of the [RunningHub Standard Model API](https://www.runninghub.cn/call-api/standard-api), with additional Seedance2.0 asset management nodes.

The project currently includes 238 standard model API nodes covering image generation, video generation, audio synthesis, 3D modeling, text understanding, and image/video upscaling. Together with 3 Seedance2.0 asset helper nodes and 1 settings node, it provides 242 ComfyUI nodes in total. You can access RunningHub standard model capabilities directly inside ComfyUI workflows and reuse Seedance2.0 assets through a unified `asset_ids` input or the `real_person_mode` toggle — no local GPU required, zero cold-start latency.

## 📌 Features

- **Node Count** — 242 ComfyUI nodes in total: 238 standard model nodes, 3 Seedance2.0 asset nodes, and 1 settings node
- **Plug & Play** — No model downloads, no GPU needed — just an API Key
- **Dynamic Registration** — Nodes are auto-generated from a JSON registry; adding new models requires only a registry update
- **Media Support** — Automatic upload/download/conversion for images, videos, and audio, seamlessly integrated with ComfyUI native types
- **Asset Management** — 3 Seedance2.0 asset helper nodes, plus a unified `asset_ids` input or `real_person_mode` workflow for Seedance2.0 / Seedance2.0-Fast image/video inputs
- **Flexible Configuration** — Three configuration methods: node settings, environment variables, or `.env` file
- **Progress Tracking** — Real-time polling progress display after task submission
- **Robust Error Handling** — Submit/upload/poll all have retry with exponential backoff, auto-distinguishing retryable vs non-retryable errors
- **Skip Error** — Every node supports a `skip_error` toggle; when enabled, errors produce type-appropriate placeholders instead of stopping the workflow
- **Example Workflows** — Includes importable example workflows covering major model capabilities

## 🎨 Supported Models

### Image Generation (53 Nodes)

| Model | RH Platform Name | Capabilities | Nodes |
|-------|-----------------|-------------|-------|
| Nano Banana V1 | 全能图片 V1 / V1 Official Stable | Text-to-Image, Image-to-Image | 4 |
| Nano Banana V2 (Gemini 3.1 Flash) | 全能图片 V2 / V2 Official | Text-to-Image, Image-to-Image | 4 |
| Nano Banana Pro | 全能图片 PRO / PRO Official | Text-to-Image, Image-to-Image, Ultra | 6 |
| GPT Image 1.5 (OpenAI) | 全能图片 G-1.5 / G-1.5 Official | Text-to-Image, Image-to-Image | 4 |
| Grok 3 / Grok 4 Image (xAI) | 全能图片 X-3 / X-4 | Text-to-Image, Image-to-Image | 4 |
| Grok Image Low-Price Channel (xAI) | 全能图片 X | Text-to-Image, Image-to-Image | 2 |
| Qwen Image 2.0 / 2.0 Pro (Alibaba) | 千问 | Text-to-Image, Image Editing | 4 |
| Wan 2.5 / 2.7 (Alibaba) | — | Text-to-Image, Image Edit | 6 |
| Higgsfield | — | Image-to-Image (Soul) | 1 |
| TopazLabs | — | Image Upscale: Standard V2 / Low Res V2 / CGI / High Fidelity V2 / Text Refine | 5 |
| Seedream v4 / v4.5 / v5 Lite (ByteDance) | — | Text-to-Image, Image-to-Image | 6 |
| FLUX Dev (Black Forest Labs) | — | Text-to-Image, Text-to-Image LoRA | 2 |
| Midjourney | 悠船 | Text-to-Image v6/v6.1/niji6/niji7/v7 | 5 |

### Video Generation (142 Nodes)

| Model | RH Platform Name | Capabilities | Nodes |
|-------|-----------------|-------------|-------|
| Sora 2 (OpenAI) | 全能视频 S / S Official | Text/Image-to-Video, Pro, Character Upload, Async | 13 |
| Google Veo 3.1 / 3.1 Lite | 全能视频 V3.1 / Veo 3.1 Lite Official Stable | Fast/Pro/Lite Text/Image/Start-End-to-Video, Reference, Video Extend | 16 |
| Grok Imagine (xAI) | 全能视频 G / G Official | Text/Image-to-Video, Edit Video | 5 |
| Kling (Kuaishou) | — | v2.5/v2.6/v3.0/o1/o3, Text/Image/Start-End/Reference/Motion Control/Edit/Elements/Lip Sync | 30 |
| Vidu (Shengshu) | — | q2/q3, Text/Image/Start-End/Reference-to-Video, Pro Fast | 19 |
| Wan 2.5 / 2.6 / 2.7 (Alibaba) | — | Text/Image/Reference-to-Video, Flash, Video Continuation | 11 |
| MiniMax Hailuo | — | 02/2.3/2.3-fast, Text/Image/Start-End-to-Video | 13 |
| Seedance v1.5 / 2.0 (ByteDance) | — | Text/Image/Multimodal-to-Video, Fast, Reference-to-Video | 11 |
| Runway Gen-4 Turbo / Aleph / SD2.0 Trial | 全能视频R | Image-to-Video, Video Editing, Trial Video Generation | 5 |
| LTX-2 19B (Lightricks) | — | Text-to-Video LoRA | 1 |
| PixVerse v5.5 / v5.6 / v6 | — | Text/Image-to-Video, Transition, Effects | 9 |
| Higgsfield | — | Image-to-Video (Dop) | 1 |
| SkyReels V3/V4 (Kunlun) | — | Text/Image-to-Video, Reference, Restyling, Video Extension | 7 |
| TopazLabs | — | Video Enhancement & Upscaling | 1 |

### Text Understanding (17 Nodes)

| Model | RH Platform Name | Capabilities | Nodes |
|-------|-----------------|-------------|-------|
| Gemini 3 Flash Preview (Google) | RHArt Text G-3 Flash Preview | Image-to-Text, CV Image-to-Text, Text-to-Text, Video Understanding | 4 |
| Gemini 3 Pro Preview (Google) | RHArt Text G-3 Pro Preview | Image-to-Text, CV Image-to-Text, Text-to-Text, Video Understanding | 4 |
| Gemini 2.5 Flash (Google) | RHArt Text G-2.5 Flash | Image-to-Text, CV Image-to-Text, Text-to-Text, Video Understanding | 4 |
| Gemini 2.5 Pro (Google) | RHArt Text G-2.5 Pro | Image-to-Text, CV Image-to-Text, Text-to-Text, Video Understanding | 4 |
| Qwen 27B Chat (Alibaba) | RHArt Text Qwen 27B | Multi-turn Chat | 1 |

### Audio Synthesis (9 Nodes)

| Model Series | Capabilities | Nodes |
|-------------|-------------|-------|
| Minimax Speech | 02/2.6/2.8 HD & Turbo | 6 |
| Minimax Music 2.5 | Text-to-Music | 1 |
| Minimax Voice Clone / Voice Design | Voice Cloning, Voice Design | 2 |

### 3D Modeling (12 Nodes)

| Model Series | Capabilities | Nodes |
|-------------|-------------|-------|
| Hunyuan 3D v3.1 | Text-to-3D, Image-to-3D | 2 |
| HiTem3D V1.5 / V2 | Image-to-3D, Multi-Image-to-3D | 4 |
| HiTem3D Portrait V1.5 / V2.0 / V2.1 | Portrait Image-to-3D, Multi-Image-to-3D | 6 |

### Seedance2.0 Assets (3 Nodes)

- User-facing nodes: `RH Seedance2.0 Asset/Create`, `RH Seedance2.0 Asset/Query`, `RH Seedance2.0 Asset IDs/Merge`
- `RH Seedance2.0 Asset/Create` always uses the fixed asset group `group-20260327004931-dvjbj` and the fixed asset name `RHas01`
- Seedance2.0 integration: `RH Seedance2.0 / Seedance2.0-Fast` image-to-video and multimodal-video nodes expose a unified `asset_ids` input and two extra widgets: `real_person_mode` and `conversion_slots`
- `asset_ids` supports a single asset ID, an `asset://<asset_ID>` URL, comma/newline separated values, or a JSON array string
- `real_person_mode=false` keeps the original direct-upload path; `real_person_mode=true` converts selected local image/video slots to Seedance2.0 assets before the API request
- `conversion_slots` defaults to `all`
- Image-to-video supports: `first_frame,last_frame`
- Multimodal video supports: `image1..image9,video1..video3`
- If asset creation fails for one slot, that slot automatically falls back to the original upload path
- Both inputs now include hover tooltips so users can quickly see usage and supported slot names

## 🛠️ Installation

### Method 1: Via ComfyUI Manager (Recommended)

Search for `ComfyUI_RH_OpenAPI` in ComfyUI Manager and install.

### Method 2: Manual Installation

```bash
cd ComfyUI/custom_nodes
git clone https://github.com/HM-RunningHub/ComfyUI_RH_OpenAPI.git
cd ComfyUI_RH_OpenAPI
pip install -r requirements.txt
```

Restart ComfyUI after installation.

## ⚙️ Configuration

You need a RunningHub API Key. Register and get one at the [RunningHub API Console](https://www.runninghub.cn/enterprise-api/sharedApi).

### Option 1: Node Settings (Recommended)

Add the **RH OpenAPI Settings** node to your canvas, fill in `base_url` and `apiKey`, then connect it to any model node.

### Option 2: Environment Variables

```bash
export RH_API_BASE_URL=https://www.runninghub.cn/openapi/v2
export RH_API_KEY=your-api-key-here
```

### Option 3: .env File

```bash
cp config/.env.example config/.env
# Edit config/.env with your API Key
```

**Priority**: Node Settings > Environment Variables > `.env` File

> **Tip**: If `RH_API_BASE_URL` and `RH_API_KEY` are already configured via environment variables or `config/.env`, the `api_config` input on every node becomes optional — you can run nodes directly without connecting the **RH OpenAPI Settings** node.

## 🚀 Usage

1. Configure your API Key (see Configuration above)
2. Find the `RunningHub` category in the ComfyUI node menu
3. Select the model node you need, or use asset management nodes under `RunningHub > Seedance2.0 Assets`
4. Wire the workflow and run it

### Example Workflows

The project includes 239 example workflow JSON files in the `examples/` directory, including 3 Seedance2.0 asset-related workflows. Download and import directly into ComfyUI.

## 📁 Project Structure

```
ComfyUI_RH_OpenAPI/
├── __init__.py              # Entry point, registers all nodes
├── models_registry.json     # Model registry (238 model definitions)
├── config/
│   └── .env.example         # Configuration template
├── core/                    # Core infrastructure
│   ├── base.py              # Base node classes (unified execution flow)
│   ├── api_key.py           # API Key configuration resolver
│   ├── rest.py              # Synchronous REST request helper
│   ├── upload.py            # File upload utility
│   ├── task.py              # Task submit & poll logic
│   ├── image.py             # Image utilities (Tensor ↔ PIL)
│   ├── video.py             # Video download utilities
│   └── audio.py             # Audio download/convert utilities
├── nodes/                   # Node implementations
│   ├── settings_node.py     # RH OpenAPI Settings node
│   ├── node_factory.py      # Dynamic node factory
│   └── assets/              # Seedance2.0 asset management nodes
└── examples/                # 239 example workflows
```

## 🔧 Architecture

This project uses a **data-driven + factory pattern** architecture:

1. **Model Registry** (`models_registry.json`) — Describes each model's endpoint, parameters, and output type in JSON
2. **Node Factory** (`node_factory.py`) — Reads the registry and auto-generates ComfyUI node classes
3. **Unified Execution Flow** (`core/base.py`) — `Prepare Inputs → Upload Media → Submit Task → Poll Status → Process Result`
4. **Media Utilities** (`core/image.py`, `video.py`, `audio.py`) — Handle format conversion between ComfyUI native types and API formats

Adding a new standard model only requires a JSON entry in the registry — no Python code needed. Seedance2.0 asset management nodes are implemented as hand-written REST wrappers.

## 📝 Notes

- API calls consume RunningHub account credits — monitor your usage
- Video generation tasks may take up to 10 minutes — please be patient
- Image/video uploads have file size limits — see individual node parameter descriptions

## 📄 License

This project is licensed under the [Apache License 2.0](LICENSE).

## 🔗 Links

- [RunningHub Website](https://www.runninghub.cn)
- [RunningHub Standard Model API](https://www.runninghub.cn/call-api/standard-api)
- [RunningHub API Console (Get API Key)](https://www.runninghub.cn/enterprise-api/sharedApi)
- [API Call Records](https://www.runninghub.cn/call-api/call-record) — View your API call history, status, and details
- [Model Pricing Overview](https://www.runninghub.cn/third-party-fees) — Pricing for all available models
- [ComfyUI](https://github.com/comfyanonymous/ComfyUI)
