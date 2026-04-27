# ComfyUI_RH_OpenAPI

![License](https://img.shields.io/badge/License-Apache%202.0-green)
![Nodes](https://img.shields.io/badge/Nodes-279-blue)
![ComfyUI](https://img.shields.io/badge/ComfyUI-Custom%20Node-orange)

[English](README_EN.md) | **中文**

**ComfyUI_RH_OpenAPI** 是 [RunningHub 标准模型 API](https://www.runninghub.cn/call-api/standard-api) 的 **1:1 ComfyUI 实现**，并额外补充了 Seedance2.0 素材资产管理节点。

本项目当前收录 275 个标准模型 API 节点（覆盖主流最新的图像生成、视频生成、音频合成、3D 建模、文本理解、图像/视频放大），并新增 3 个 Seedance2.0 素材辅助节点与 1 个设置节点，总计提供 279 个 ComfyUI 节点，让你可以在 ComfyUI 工作流中直接调用 RunningHub 的标准模型能力，并通过统一的 `asset_ids` 输入或 `real_person_mode` 复用 Seedance2.0 素材资产，无需本地 GPU，无冷启动延迟。

## 📌 项目特点

- **节点总量** — 共 279 个 ComfyUI 节点，其中包含 275 个标准模型节点、3 个 Seedance2.0 素材节点和 1 个设置节点
- **即插即用** — 无需下载模型、无需 GPU，只需 API Key 即可调用全部能力
- **动态注册** — 基于 JSON 注册表自动生成节点，新模型上线后仅需更新注册表
- **多媒体支持** — 图片、视频、音频自动上传 / 下载 / 格式转换，与 ComfyUI 原生类型无缝衔接
- **素材资产管理** — 提供 3 个 Seedance2.0 素材辅助节点，并支持通过统一的 `asset_ids` 输入或 `real_person_mode` 把本地图片/视频映射到 Seedance2.0 / Seedance2.0-Fast 节点
- **灵活配置** — 支持节点配置、环境变量、`.env` 文件三种配置方式
- **进度显示** — 任务提交后实时显示轮询进度
- **容错机制** — 提交/上传/轮询均有重试与指数退避，自动区分可重试与不可重试错误
- **跳过错误** — 每个节点支持 `skip_error` 开关，开启后遇到错误不中断工作流，输出对应类型的错误占位符
- **示例工作流** — 提供大量可直接导入的示例工作流，覆盖主要模型能力

## 🎨 支持的模型

### 图像生成（59 个节点）

| 模型 | RH 平台名称 | 能力 | 节点数 |
|------|-----------|------|--------|
| Nano Banana V1 | 全能图片 V1 / V1 官方稳定版 | 文生图、图生图 | 4 |
| Nano Banana V2（Gemini 3.1 Flash） | 全能图片 V2 / V2 官方 | 文生图、图生图 | 4 |
| Nano Banana Pro | 全能图片 PRO / PRO 官方 | 文生图、图生图、Ultra | 6 |
| GPT Image 1.5（OpenAI） | 全能图片 G-1.5 / G-1.5 官方（旧版标记 Deprecated） | 文生图、图生图 | 4 |
| GPT Image 2.0（OpenAI） | 全能图片 G-2 / G-2 官方 | 文生图、图生图 | 4 |
| Grok 3 / Grok 4 Image（xAI） | 全能图片 X-3 / X-4 | 文生图、图生图 | 4 |
| Grok Image 低价通道（xAI） | 全能图片 X | 文生图、图生图 | 2 |
| Grok Image 官方（xAI） | 全能图片 X 官方 | 文生图、图像编辑 | 2 |
| Qwen Image 2.0 / 2.0 Pro（阿里巴巴） | 千问 | 文生图、图像编辑 | 4 |
| Wan 万相 2.5 / 2.7（阿里巴巴） | — | 文生图、图像编辑 | 6 |
| Higgsfield | — | 图生图（Soul） | 1 |
| TopazLabs | — | 图像放大 Standard V2 / Low Res V2 / CGI / High Fidelity V2 / Text Refine | 5 |
| Seedream v4 / v4.5 / v5 Lite（字节跳动） | — | 文生图、图生图 | 6 |
| FLUX Dev（Black Forest Labs） | — | 文生图、文生图 LoRA | 2 |
| Midjourney | 悠船 | 文生图 v6/v6.1/niji6/niji7/v7 | 5 |

### 视频生成（171 个节点）

| 模型 | RH 平台名称 | 能力 | 节点数 |
|------|-----------|------|--------|
| Sora 2（OpenAI） | 全能视频 S / S 官方 | 文/图生视频、Pro、角色上传、异步 | 12 |
| Google Veo 3.1 / 3.1 Lite（Google） | 全能视频 V3.1 / V3.1 Lite（Fast/Pro/Lite 官方 + 低价通道） | Fast/Pro/Lite 文/图/首尾帧生视频、参考生视频、视频扩展 | 18 |
| Grok Imagine（xAI） | 全能视频 G / G 官方 | 文/图/参考生视频、视频扩展、编辑视频 | 7 |
| Kling 可灵（快手） | — | v2.5/v2.5-turbo/v2.6/v3.0/v3-4k/v3.0-4k/o1/o3/o3-4k，文/图/首尾帧/参考/动作控制/编辑/元素/口型同步 | 36 |
| Vidu（生数科技） | — | q2/q3，文/图/首尾帧/参考生视频、Pro Fast、Turbo | 20 |
| Wan 万相 2.5 / 2.6 / 2.7（阿里巴巴） | — | 文/图/参考生视频、Flash、视频编辑、视频续写 | 12 |
| Happyhorse 1.0（阿里巴巴） | — | 文/图生视频 | 2 |
| MiniMax Hailuo 海螺 | — | 02/2.3/2.3-fast，文/图/首尾帧生视频 | 13 |
| Seedance v1.5 / 2.0 / 2.0 Global（字节跳动） | — | 文/图/多模态生视频、Fast、Global、参考生视频 | 17 |
| Runway Gen-4 Turbo / Aleph | 全能视频 R | 图生视频、视频编辑 | 3 |
| LTX-2 19B（Lightricks） | — | 文生视频 LoRA | 1 |
| PixVerse v5.5 / v5.6 / v6 / C1 | — | 文/图/参考生视频、转场、特效、视频扩展 | 14 |
| Higgsfield | — | 图生视频（Dop） | 1 |
| SkyReels V3/V4（昆仑万维） | — | 文/图生视频、参考生视频、视频风格化、视频扩展 | 7 |
| TopazLabs | — | 视频增强放大 | 1 |
| Midjourney（悠船） | — | 图生视频 | 1 |
| RhartVideo 增强 / 参考 | — | 视频 Upscale、FPS 增强、Cinematic、Seedance 参考生视频 | 4 |

### 文本理解（17 个节点）

| 模型 | RH 平台名称 | 能力 | 节点数 |
|------|-----------|------|--------|
| Gemini 3 Flash Preview（Google） | RHArt Text G-3 Flash Preview | 图生文、CV 图生文、文生文、视频理解 | 4 |
| Gemini 3 Pro Preview（Google） | RHArt Text G-3 Pro Preview | 图生文、CV 图生文、文生文、视频理解 | 4 |
| Gemini 2.5 Flash（Google） | RHArt Text G-2.5 Flash | 图生文、CV 图生文、文生文、视频理解 | 4 |
| Gemini 2.5 Pro（Google） | RHArt Text G-2.5 Pro | 图生文、CV 图生文、文生文、视频理解 | 4 |
| Qwen 2.7B Chat（阿里巴巴） | RHArt Text Qwen 27B | 多轮对话 | 1 |

### 音频合成（16 个节点）

| 模型系列 | 能力 | 节点数 |
|---------|------|--------|
| Minimax Speech | 02/2.6/2.8 HD & Turbo | 6 |
| Minimax Music 2.5 | 文生音乐 | 1 |
| Minimax Voice Clone / Voice Design | 声音克隆、音色设计 | 2 |
| Suno v4.5 / v5 / v5.5（RHArt） | Single / Custom 文生音乐 | 6 |
| Suno Lyrics（RHArt） | 歌词生成 | 1 |

### 3D 建模（12 个节点）

| 模型系列 | 能力 | 节点数 |
|---------|------|--------|
| 混元 3D v3.1 | 文生 3D、图生 3D | 2 |
| HiTem3D V1.5 / V2 | 图生 3D、多图生 3D | 4 |
| HiTem3D Portrait V1.5 / V2.0 / V2.1 | 人像图生 3D、多图生 3D | 6 |

### Seedance2.0 素材资产（3 个节点）

- 用户节点：`RH Seedance2.0素材/创建`、`RH Seedance2.0素材/查询`、`RH Seedance2.0素材ID/合并`
- `RH Seedance2.0素材/创建` 使用固定素材组 `group-20260327004931-dvjbj`，并固定素材名称为 `RHas01`
- Seedance2.0 适配：`RH Seedance2.0 / Seedance2.0-Fast` 的图生视频、多模态视频节点提供统一的 `asset_ids` 输入，并新增 `real_person_mode`、`conversion_slots`
- `asset_ids` 支持单个素材 ID、`asset://<asset_ID>`、逗号/换行分隔，以及 JSON 数组字符串
- `real_person_mode=false` 时保持原始本地上传行为；`real_person_mode=true` 时会把选中的本地图片/视频槽位先转成素材，再写入 Seedance2.0 payload
- `conversion_slots` 默认 `all`
- 图生视频支持：`first_frame,last_frame`
- 多模态视频支持：`image1..image9,video1..video3`
- 某个槽位转素材失败时会自动回退到原始上传，不影响其它槽位
- 这两个输入都补充了 hover 提示，鼠标悬停即可查看说明和可用槽位格式

## 🛠️ 安装

### 方式一：通过 ComfyUI Manager 安装（推荐）

在 ComfyUI Manager 中搜索 `ComfyUI_RH_OpenAPI` 并安装。

### 方式二：手动安装

```bash
cd ComfyUI/custom_nodes
git clone https://github.com/HM-RunningHub/ComfyUI_RH_OpenAPI.git
cd ComfyUI_RH_OpenAPI
pip install -r requirements.txt
```

安装完成后重启 ComfyUI。

## ⚙️ 配置

使用本插件前，你需要一个 RunningHub API Key。前往 [RunningHub API 控制台](https://www.runninghub.cn/enterprise-api/sharedApi) 注册账号并获取 API Key。

### 配置方式一：节点配置（推荐）

在 ComfyUI 画布中添加 **RH OpenAPI Settings** 节点，填入 `base_url` 和 `apiKey`，然后连接到任意模型节点即可。

### 配置方式二：环境变量

```bash
export RH_API_BASE_URL=https://www.runninghub.cn/openapi/v2
export RH_API_KEY=your-api-key-here
```

### 配置方式三：.env 文件

```bash
cp config/.env.example config/.env
# 编辑 config/.env，填入你的 API Key
```

**配置优先级**：节点配置 > 环境变量 > `.env` 文件

> **提示**：如果已通过环境变量或 `config/.env` 配置了 `RH_API_BASE_URL` 和 `RH_API_KEY`，则每个节点的 `api_config` 输入为可选项，无需连接 **RH OpenAPI Settings** 节点即可直接运行。

## 🚀 使用方法

1. 配置好 API Key（参见上方配置说明）
2. 在 ComfyUI 节点菜单中找到 `RunningHub` 分类
3. 选择你需要的模型节点，或在 `RunningHub > Seedance2.0 Assets` 下选择素材管理节点
4. 连线后运行即可

### 示例工作流

项目在 `examples/` 目录下提供了 249 个示例工作流 JSON 文件，其中包含 3 个 Seedance2.0 素材相关工作流。下载后直接导入 ComfyUI 即可使用。

## 📁 项目结构

```
ComfyUI_RH_OpenAPI/
├── __init__.py              # 入口文件，注册所有节点
├── models_registry.json     # 模型注册表（275 个模型定义）
├── config/
│   └── .env.example         # 配置文件示例
├── core/                    # 核心基础设施
│   ├── base.py              # 节点基类（统一执行流程）
│   ├── api_key.py           # API Key 配置解析
│   ├── rest.py              # 同步 REST 请求封装
│   ├── upload.py            # 文件上传
│   ├── task.py              # 任务提交与轮询
│   ├── image.py             # 图像工具（Tensor ↔ PIL）
│   ├── video.py             # 视频下载工具
│   └── audio.py             # 音频下载/转换工具
├── nodes/                   # 节点实现
│   ├── settings_node.py     # RH OpenAPI Settings 配置节点
│   ├── node_factory.py      # 动态节点工厂
│   └── assets/              # Seedance2.0 素材资产节点
└── examples/                # 249 个示例工作流
```

## 🔧 架构说明

本项目采用 **数据驱动 + 工厂模式** 架构：

1. **模型注册表**（`models_registry.json`）— 以 JSON 格式描述每个模型的端点、参数、输出类型
2. **节点工厂**（`node_factory.py`）— 读取注册表，自动生成 ComfyUI 节点类
3. **统一执行流程**（`core/base.py`）— `准备输入 → 上传媒体 → 提交任务 → 轮询状态 → 处理结果`
4. **媒体工具**（`core/image.py`, `video.py`, `audio.py`）— 负责 ComfyUI 原生类型与 API 之间的格式转换

新增标准模型只需在注册表中添加一条 JSON 记录，无需编写任何 Python 代码；Seedance2.0 素材管理节点则采用手写 REST 封装。

## 📝 注意事项

- 调用 API 会消耗 RunningHub 账户余额，请关注用量
- 视频生成任务可能需要较长时间（最长 10 分钟），请耐心等待
- 图片/视频上传有文件大小限制，具体限制见各节点参数说明

## 📄 许可证

本项目基于 [Apache License 2.0](LICENSE) 开源。

## 🔗 相关链接

- [RunningHub 官网](https://www.runninghub.cn)
- [RunningHub 标准模型 API](https://www.runninghub.cn/call-api/standard-api)
- [RunningHub API 控制台（获取 API Key）](https://www.runninghub.cn/enterprise-api/sharedApi)
- [API 调用记录查询](https://www.runninghub.cn/call-api/call-record) — 查看历史调用状态与详情
- [所有模型价格汇总表](https://www.runninghub.cn/third-party-fees) — 各模型计费标准一览
- [ComfyUI](https://github.com/comfyanonymous/ComfyUI)
