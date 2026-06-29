# ComfyUI_RH_OpenAPI

![License](https://img.shields.io/badge/License-Apache%202.0-green)
![Nodes](https://img.shields.io/badge/Nodes-364-blue)
![ComfyUI](https://img.shields.io/badge/ComfyUI-Custom%20Node-orange)

**English** | [中文](README.md)

**ComfyUI_RH_OpenAPI** is a **1:1 ComfyUI implementation** of the [RunningHub Standard Model API](https://www.runninghub.cn/call-api/standard-api), with additional Seedance2.0 asset management nodes.

The project currently includes 359 standard model API nodes covering image generation, video generation, audio synthesis, 3D modeling, text understanding, and image/video upscaling. Together with 3 Seedance2.0 asset helper nodes, 1 RunningHub LLM chat node, and 1 settings node, it provides 364 ComfyUI nodes in total. You can access RunningHub standard model and LLM capabilities directly inside ComfyUI workflows and reuse Seedance2.0 assets through a unified `asset_ids` input or the `real_person_mode` toggle — no local GPU required, zero cold-start latency.

## 📌 Features

- **Node Count** — 364 ComfyUI nodes in total: 359 standard model nodes, 3 Seedance2.0 asset nodes, 1 RunningHub LLM chat node, and 1 settings node
- **Plug & Play** — No model downloads, no GPU needed — just an API Key
- **Dynamic Registration** — Nodes are auto-generated from a JSON registry; adding new models requires only a registry update
- **Media Support** — Automatic upload/download/conversion for images, videos, and audio, seamlessly integrated with ComfyUI native types
- **Asset Management** — 3 Seedance2.0 asset helper nodes, plus a unified `asset_ids` input or `real_person_mode` workflow for Seedance2.0 / Seedance2.0-Fast image/video inputs
- **LLM Chat Completions** — Adds the `RH LLM Chat Completions` node with dynamic model discovery, text chat, image understanding, and video understanding
- **Flexible Configuration** — Three configuration methods: node settings, environment variables, or `.env` file
- **Progress Tracking** — Real-time polling progress display after task submission
- **Robust Error Handling** — Submit/upload/poll all have retry with exponential backoff, auto-distinguishing retryable vs non-retryable errors
- **Skip Error** — Every node supports a `skip_error` toggle; when enabled, errors produce type-appropriate placeholders instead of stopping the workflow
- **Example Workflows** — Includes importable example workflows covering major model capabilities

## 🎨 Supported Models

### Image Generation (78 Nodes)

| Model | RH Platform Name | Capabilities | Nodes |
|-------|-----------------|-------------|-------|
| Nano Banana V1 | 全能图片 V1 / V1 Official Stable | Text-to-Image, Image-to-Image | 4 |
| Nano Banana V2 (Gemini 3.1 Flash) | 全能图片 V2 / V2 Official | Text-to-Image, Image-to-Image | 4 |
| Nano Banana Pro | 全能图片 PRO / PRO Official | Text-to-Image, Image-to-Image, Ultra | 6 |
| GPT Image 1.5 (OpenAI) | 全能图片 G-1.5 / G-1.5 Official (older flavours marked Deprecated) | Text-to-Image, Image-to-Image | 4 |
| GPT Image 2.0 (OpenAI) | 全能图片 G-2 / G-2 Official | Text-to-Image, Image-to-Image | 4 |
| Grok 3 / Grok 4 Image (xAI) | 全能图片 X-3 / X-4 | Text-to-Image, Image-to-Image | 4 |
| Grok Image Low-Price Channel (xAI) | 全能图片 X | Text-to-Image, Image-to-Image | 2 |
| Grok Image Official (xAI) | 全能图片 X 官方 | Text-to-Image, Image Editing | 2 |
| Grok Imagine Image Quality (xAI) | RHArt Imagine Image Quality | Text-to-Image, Image Editing, high-quality multi-image output | 2 |
| Qwen Image 2.0 / 2.0 Pro (Alibaba) | 千问 | Text-to-Image, Image Editing | 4 |
| Wan 2.5 / 2.7 (Alibaba) | — | Text-to-Image, Image Edit | 6 |
| Higgsfield | — | Image-to-Image (Soul) | 1 |
| HYPIR Image Enhancement | — | HYPIR-ULTRA, HYPIR-BALANCE | 2 |
| TopazLabs | — | Image Upscale: Standard V2 / Low Res V2 / CGI / High Fidelity V2 / Text Refine | 5 |
| Seedream v4 / v4.5 / v5 Lite / Jimeng 4.6 (ByteDance) | — | Text-to-Image, Image-to-Image | 8 |
| FLUX Dev (Black Forest Labs) | — | Text-to-Image, Text-to-Image LoRA | 2 |
| Midjourney | 悠船 | Text-to-Image v6/v6.1/niji6/niji7/v7/v8.1 | 6 |
| Marble 1.0 / 1.1 / 1.1 Plus | — | Image/Multi-Image-to-3D World | 6 |
| Luma Uni-1 / Uni-1 Max | — | Text-to-Image, Image-to-Image, Image Editing | 6 |

### Video Generation (229 Nodes)

| Model | RH Platform Name | Capabilities | Nodes |
|-------|-----------------|-------------|-------|
| Sora 2 (OpenAI) | 全能视频 S / S Official | Text/Image-to-Video, Pro, Character Upload, Async | 12 |
| Google Veo 3.1 / 3.1 Lite | 全能视频 V3.1 / V3.1 Lite (Fast/Pro/Lite Official + Low-Price) | Fast/Pro/Lite Text/Image/Start-End-to-Video, Reference, Video Extend | 19 |
| Gemini Omni Flash (Google) | Gemini Omni Flash | Text/Image-to-Video, Video Editing | 3 |
| Grok Imagine (xAI) | 全能视频 G / G Official | Text/Image/Reference-to-Video, Video Extend, Edit Video | 8 |
| Kling (Kuaishou) | — | v2.5/v2.5-turbo/v2.6/v3.0/v3-4k/v3.0-4k/o1/o3/o3-4k, Text/Image/Start-End/Reference/Motion Control/Edit/Elements/Advanced Elements/Lip Sync/AI Avatar | 40 |
| Vidu (Shengshu) | — | q2/q3, Text/Image/Start-End/Reference-to-Video, Pro Fast, Turbo, short-play video | 22 |
| Wan 2.5 / 2.6 / 2.7 (Alibaba) | — | Text/Image/Reference-to-Video, Flash, Spicy, Video Editing, Video Continuation | 13 |
| HappyHorse 1.0 / 1.1 (Alibaba) | — | Text/Image/Reference-to-Video, Video Editing | 7 |
| MiniMax Hailuo | — | 02/2.3/2.3-fast, Text/Image/Start-End-to-Video | 13 |
| Seedance v1.5 / 2.0 / 2.0 Global / Volc tools (ByteDance) | — | Text/Image/Multimodal-to-Video, Fast, Global, Reference-to-Video, drama translation, subtitle removal | 27 |
| Runway Gen-4 Turbo / Aleph | 全能视频 R | Image-to-Video, Video Editing | 3 |
| LTX-2 19B (Lightricks) | — | Text-to-Video LoRA | 1 |
| PixVerse v5.5 / v5.6 / v6 / C1 | — | Text/Image/Reference-to-Video, Transition, Effects, Extend | 15 |
| Higgsfield | — | Image-to-Video (Dop) | 1 |
| SkyReels V3/V4 (Kunlun) | — | Text/Image-to-Video, Reference, Omni Reference, Restyling, Video Extension | 10 |
| TopazLabs | — | Video Enhancement & Upscaling | 1 |
| Midjourney (Youchuan) | — | Image-to-Video | 1 |
| RhartVideo Enhancement / Reference / Character | — | Video Upscale, FPS Increaser, Cinematic, DreamActor, Seedance Reference-to-Video | 5 |
| Marble 1.0 / 1.1 / 1.1 Plus | — | Text/Video-to-3D World, Media Asset Upload | 7 |
| Mureka v7.6 / v8 / v9 / O2 | — | File Upload, Song/Instrumental Generation, Song Extension, Vocal Clone, Lyrics Generation, song recognition, stem separation | 17 |

### Text Understanding (17 Nodes)

| Model | RH Platform Name | Capabilities | Nodes |
|-------|-----------------|-------------|-------|
| Gemini 3 Flash Preview (Google) | RHArt Text G-3 Flash Preview | Image-to-Text, CV Image-to-Text, Text-to-Text, Video Understanding | 4 |
| Gemini 3 Pro Preview (Google) | RHArt Text G-3 Pro Preview | Image-to-Text, CV Image-to-Text, Text-to-Text, Video Understanding | 4 |
| Gemini 2.5 Flash (Google) | RHArt Text G-2.5 Flash | Image-to-Text, CV Image-to-Text, Text-to-Text, Video Understanding | 4 |
| Gemini 2.5 Pro (Google) | RHArt Text G-2.5 Pro | Image-to-Text, CV Image-to-Text, Text-to-Text, Video Understanding | 4 |
| Qwen 27B Chat (Alibaba) | RHArt Text Qwen 27B | Multi-turn Chat | 1 |

### Audio Synthesis (19 Nodes)

| Model Series | Capabilities | Nodes |
|-------------|-------------|-------|
| Minimax Speech | 02/2.6/2.8 HD & Turbo | 6 |
| Minimax Music 2.5 / 2.6 / Cover | Text-to-Music, music cover, cover preprocessing | 4 |
| Minimax Voice Clone / Voice Design | Voice Cloning, Voice Design | 2 |
| Suno v4.5 / v5 / v5.5 (RHArt) | Single / Custom text-to-music | 6 |
| Suno Lyrics (RHArt) | Lyric generation | 1 |

### 3D Modeling (16 Nodes)

| Model Series | Capabilities | Nodes |
|-------------|-------------|-------|
| Hunyuan 3D v3.1 | Text-to-3D, Image-to-3D | 2 |
| HiTem3D V1.5 / V2 / V2.1 | Image-to-3D, Multi-Image-to-3D | 6 |
| HiTem3D Portrait V1.5 / V2.0 / V2.1 | Portrait Image-to-3D, Multi-Image-to-3D | 6 |
| Meshy6 | Text-to-3D, Image-to-3D | 2 |

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

### RunningHub LLM Chat (1 Node)

- Node name: `RH LLM Chat Completions`
- Dynamically loads model IDs from `https://llm.runninghub.ai/v1/models`, with a built-in fallback list when the network is unavailable
- Calls the OpenAI-compatible endpoint: CN uses `https://llm.runninghub.cn/v1/chat/completions`, HK uses `https://llm.runninghub.ai/v1/chat/completions`
- Supports text chat, image understanding, and video understanding; when both images and video are connected, images take priority
- Image inputs are converted to JPEG and passed inline as Base64 `image_url` payloads, without uploading to RunningHub OpenAPI first
- Video inputs are compressed to at most 15 seconds and 10MB when needed, then passed to the LLM gateway as `video_url`
- The `seed` input is kept for ComfyUI workflow compatibility but is not forwarded to the LLM gateway because some upstream models reject it
- The `api_config` input is placed at the last slot; when left unconnected, the node uses the system shared API key, environment variables, or `.env` configuration

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

The project includes 319 example workflow JSON files in the `examples/` directory, including 3 Seedance2.0 asset-related workflows. Download and import directly into ComfyUI.

## 📁 Project Structure

```
ComfyUI_RH_OpenAPI/
├── __init__.py              # Entry point, registers all nodes
├── models_registry.json     # Model registry (359 model definitions)
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
│   ├── llm_chat.py          # RunningHub LLM Chat Completions node
│   ├── node_factory.py      # Dynamic node factory
│   └── assets/              # Seedance2.0 asset management nodes
└── examples/                # 319 example workflows
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
