# ComfyUI_RH_OpenAPI

![License](https://img.shields.io/badge/License-Apache%202.0-green)
![Nodes](https://img.shields.io/badge/Nodes-110%2B-blue)
![ComfyUI](https://img.shields.io/badge/ComfyUI-Custom%20Node-orange)

**English** | [中文](README.md)

**ComfyUI_RH_OpenAPI** is a **1:1 ComfyUI implementation** of the [RunningHub Standard Model API](https://www.runninghub.cn/call-api/standard-api).

RunningHub provides 110+ standard model APIs covering image generation, video generation, audio synthesis, and 3D modeling. This project converts every API endpoint into a corresponding ComfyUI node, enabling you to access all RunningHub model capabilities directly within ComfyUI workflows — no local GPU required, zero cold-start latency.

## 📌 Features

- **Full Coverage** — 110+ ComfyUI nodes, mapping 1:1 to [RunningHub Standard Model API](https://www.runninghub.cn/call-api/standard-api)
- **Plug & Play** — No model downloads, no GPU needed — just an API Key
- **Dynamic Registration** — Nodes are auto-generated from a JSON registry; adding new models requires only a registry update
- **Media Support** — Automatic upload/download/conversion for images, videos, and audio, seamlessly integrated with ComfyUI native types
- **Flexible Configuration** — Three configuration methods: node settings, environment variables, or `.env` file
- **Progress Tracking** — Real-time polling progress display after task submission
- **Example Workflows** — Every node comes with an importable example workflow

## 🎨 Supported Models

### Image Generation (20 Nodes)

| Model Series | Capabilities | Nodes |
|-------------|-------------|-------|
| RHArt Image V1 | Text-to-Image, Image-to-Image | 2 |
| RHArt Image PRO | Text-to-Image, Image-to-Image | 2 |
| RHArt Image PRO Official | Text-to-Image, Image-to-Image, Ultra | 4 |
| RHArt Image G-1.5 | Text-to-Image, Image-to-Image | 2 |
| Seedream v4 / v4.5 | Text-to-Image, Image-to-Image | 4 |
| Youchuan | Text-to-Image (v6/v61/niji6/niji7/v7), Image-to-Video | 6 |

### Video Generation (80 Nodes)

| Model Series | Capabilities | Nodes |
|-------------|-------------|-------|
| RHArt Video S | Image/Text-to-Video, Pro, Official, Character Upload | 11 |
| RHArt Video V3.1 | Fast/Pro Text/Image-to-Video, Start-End Frame, Reference, Video Extend | 12 |
| RHArt Video G | Text/Image-to-Video | 2 |
| Kling | v2.5/v2.6/v3.0/o1/o3, Text/Image/Start-End/Reference/Motion Control/Edit | 20 |
| Vidu | q2/q3, Text/Image/Start-End/Reference-to-Video | 15 |
| Wan 2.6 | Text/Image-to-Video, Flash | 3 |
| Hailuo | 02/2.3/2.3-fast, Text/Image-to-Video | 13 |
| Seedance v1.5 | Text/Image-to-Video, Fast, Reference-to-Video | 5 |

### Audio Synthesis (8 Nodes)

| Model Series | Capabilities | Nodes |
|-------------|-------------|-------|
| Minimax Speech | 02/2.6/2.8 HD & Turbo | 6 |
| Minimax Music 2.5 | Text-to-Music | 1 |
| Minimax Voice Clone | Voice Cloning | 1 |

### 3D Modeling (2 Nodes)

| Model Series | Capabilities | Nodes |
|-------------|-------------|-------|
| Hunyuan 3D v3.1 | Text-to-3D, Image-to-3D | 2 |

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

## 🚀 Usage

1. Configure your API Key (see Configuration above)
2. Find the `RunningHub` category in the ComfyUI node menu
3. Select the model node you need, wire it up, and run

### Example Workflows

The project includes 110 example workflow JSON files in the `examples/` directory, covering every model node. Download and import directly into ComfyUI.

## 📁 Project Structure

```
ComfyUI_RH_OpenAPI/
├── __init__.py              # Entry point, registers all nodes
├── models_registry.json     # Model registry (110+ model definitions)
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
└── examples/                # 110 example workflows
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
