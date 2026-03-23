# ComfyUI_RH_OpenAPI

![License](https://img.shields.io/badge/License-Apache%202.0-green)
![Nodes](https://img.shields.io/badge/Nodes-196-blue)
![ComfyUI](https://img.shields.io/badge/ComfyUI-Custom%20Node-orange)

**English** | [中文](README.md)

**ComfyUI_RH_OpenAPI** is a **1:1 ComfyUI implementation** of the [RunningHub Standard Model API](https://www.runninghub.cn/call-api/standard-api).

RunningHub provides 196 standard model APIs covering image generation, video generation, audio synthesis, 3D modeling, text understanding, and image/video upscaling. This project converts every API endpoint into a corresponding ComfyUI node, enabling you to access all RunningHub model capabilities directly within ComfyUI workflows — no local GPU required, zero cold-start latency.

## 📌 Features

- **Full Coverage** — 196 ComfyUI nodes, mapping 1:1 to [RunningHub Standard Model API](https://www.runninghub.cn/call-api/standard-api)
- **Plug & Play** — No model downloads, no GPU needed — just an API Key
- **Dynamic Registration** — Nodes are auto-generated from a JSON registry; adding new models requires only a registry update
- **Media Support** — Automatic upload/download/conversion for images, videos, and audio, seamlessly integrated with ComfyUI native types
- **Flexible Configuration** — Three configuration methods: node settings, environment variables, or `.env` file
- **Progress Tracking** — Real-time polling progress display after task submission
- **Robust Error Handling** — Submit/upload/poll all have retry with exponential backoff, auto-distinguishing retryable vs non-retryable errors
- **Skip Error** — Every node supports a `skip_error` toggle; when enabled, errors produce type-appropriate placeholders instead of stopping the workflow
- **Example Workflows** — Every node comes with an importable example workflow

## 🎨 Supported Models

### Image Generation (46 Nodes)

| Model | RH Platform Name | Capabilities | Nodes |
|-------|-----------------|-------------|-------|
| Nano Banana V1 | 全能图片 V1 / V1 Official Stable | Text-to-Image, Image-to-Image | 4 |
| Nano Banana V2 (Gemini 3.1 Flash) | 全能图片 V2 / V2 Official | Text-to-Image, Image-to-Image | 4 |
| Nano Banana Pro | 全能图片 PRO / PRO Official | Text-to-Image, Image-to-Image, Ultra | 6 |
| GPT Image 1.5 (OpenAI) | 全能图片 G-1.5 / G-1.5 Official | Text-to-Image, Image-to-Image | 4 |
| Grok 3 / Grok 4 Image (xAI) | 全能图片 X-3 / X-4 | Text-to-Image, Image-to-Image | 4 |
| Grok Image Low-Price Channel (xAI) | 全能图片 X | Text-to-Image, Image-to-Image | 2 |
| Qwen Image 2.0 / 2.0 Pro (Alibaba) | 千问 | Text-to-Image, Image Editing | 4 |
| TopazLabs | — | Image Upscale: Standard V2 / Low Res V2 / CGI / High Fidelity V2 / Text Refine | 5 |
| Seedream v4 / v4.5 / v5 Lite (ByteDance) | — | Text-to-Image, Image-to-Image | 6 |
| FLUX Dev (Black Forest Labs) | — | Text-to-Image, Text-to-Image LoRA | 2 |
| Midjourney | 悠船 | Text-to-Image v6/v6.1/niji6/niji7/v7 | 5 |

### Video Generation (114 Nodes)

| Model | RH Platform Name | Capabilities | Nodes |
|-------|-----------------|-------------|-------|
| Sora 2 (OpenAI) | 全能视频 S / S Official | Text/Image-to-Video, Pro, Character Upload, Async | 13 |
| Google Veo 3.1 | 全能视频 V3.1 | Fast/Pro Text/Image/Start-End-to-Video, Reference, Video Extend | 13 |
| Grok Imagine (xAI) | 全能视频 G / G Official | Text/Image-to-Video, Edit Video | 5 |
| Kling (Kuaishou) | — | v2.5/v2.6/v3.0/o1/o3, Text/Image/Start-End/Reference/Motion Control/Edit/Elements/Lip Sync | 30 |
| Vidu (Shengshu) | — | q2/q3, Text/Image/Start-End/Reference-to-Video | 16 |
| Wan 2.6 (Alibaba) | — | Text/Image/Reference-to-Video, Flash | 5 |
| MiniMax Hailuo | — | 02/2.3/2.3-fast, Text/Image/Start-End-to-Video | 13 |
| Seedance v1.5 (ByteDance) | — | Text/Image-to-Video, Fast, Reference-to-Video | 5 |
| DreamActor V2 (ByteDance) | — | Digital Human Video Generation | 1 |
| Runway Gen-4 Turbo / Aleph | 全能视频R | Image-to-Video, Video Editing | 3 |
| LTX-2 19B (Lightricks) | — | Text-to-Video LoRA | 1 |
| PixVerse v5.5 | — | Text/Image-to-Video, Transition, Effects | 4 |
| SkyReels V3/V4 (Kunlun) | — | Text/Image-to-Video, Reference, Restyling, Video Extension | 7 |
| TopazLabs | — | Video Enhancement & Upscaling | 1 |

### Text Understanding (12 Nodes)

| Model | RH Platform Name | Capabilities | Nodes |
|-------|-----------------|-------------|-------|
| Gemini 3 Flash Preview (Google) | RHArt Text G-3 Flash Preview | Image-to-Text, Text-to-Text, Video Understanding | 3 |
| Gemini 3 Pro Preview (Google) | RHArt Text G-3 Pro Preview | Image-to-Text, Text-to-Text, Video Understanding | 3 |
| Gemini 2.5 Flash (Google) | RHArt Text G-2.5 Flash | Image-to-Text, Text-to-Text, Video Understanding | 3 |
| Gemini 2.5 Pro (Google) | RHArt Text G-2.5 Pro | Image-to-Text, Text-to-Text, Video Understanding | 3 |

### Audio Synthesis (8 Nodes)

| Model Series | Capabilities | Nodes |
|-------------|-------------|-------|
| Minimax Speech | 02/2.6/2.8 HD & Turbo | 6 |
| Minimax Music 2.5 | Text-to-Music | 1 |
| Minimax Voice Clone | Voice Cloning | 1 |

### 3D Modeling (12 Nodes)

| Model Series | Capabilities | Nodes |
|-------------|-------------|-------|
| Hunyuan 3D v3.1 | Text-to-3D, Image-to-3D | 2 |
| HiTem3D V1.5 / V2 | Image-to-3D, Multi-Image-to-3D | 4 |
| HiTem3D Portrait V1.5 / V2.0 / V2.1 | Portrait Image-to-3D, Multi-Image-to-3D | 6 |

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
3. Select the model node you need, wire it up, and run

### Example Workflows

The project includes 196 example workflow JSON files in the `examples/` directory, covering every model node. Download and import directly into ComfyUI.

## 📁 Project Structure

```
ComfyUI_RH_OpenAPI/
├── __init__.py              # Entry point, registers all nodes
├── models_registry.json     # Model registry (196 model definitions)
├── config/
│   └── .env.example         # Configuration template
├── core/                    # Core infrastructure
│   ├── base.py              # Base node classes (unified execution flow)
│   ├── api_key.py           # API Key configuration resolver
│   ├── upload.py            # File upload utility
│   ├── task.py              # Task submit & poll logic
│   ├── image.py             # Image utilities (Tensor ↔ PIL)
│   ├── video.py             # Video download utilities
│   └── audio.py             # Audio download/convert utilities
├── nodes/                   # Node implementations
│   ├── settings_node.py     # RH OpenAPI Settings node
│   └── node_factory.py      # Dynamic node factory
└── examples/                # 196 example workflows
```

## 🔧 Architecture

This project uses a **data-driven + factory pattern** architecture:

1. **Model Registry** (`models_registry.json`) — Describes each model's endpoint, parameters, and output type in JSON
2. **Node Factory** (`node_factory.py`) — Reads the registry and auto-generates ComfyUI node classes
3. **Unified Execution Flow** (`core/base.py`) — `Prepare Inputs → Upload Media → Submit Task → Poll Status → Process Result`
4. **Media Utilities** (`core/image.py`, `video.py`, `audio.py`) — Handle format conversion between ComfyUI native types and API formats

Adding a new model only requires a JSON entry in the registry — no Python code needed.

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
