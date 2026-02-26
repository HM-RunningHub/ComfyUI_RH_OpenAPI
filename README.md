# ComfyUI_RH_OpenAPI

![License](https://img.shields.io/badge/License-Apache%202.0-green)
![Nodes](https://img.shields.io/badge/Nodes-110%2B-blue)
![ComfyUI](https://img.shields.io/badge/ComfyUI-Custom%20Node-orange)

[English](README_EN.md) | **中文**

**ComfyUI_RH_OpenAPI** 是 [RunningHub 标准模型 API](https://www.runninghub.cn/call-api/standard-api) 的 **1:1 ComfyUI 实现**。

RunningHub 平台提供了 110+ 个标准模型 API（涵盖主流最新所有的图像生成、视频生成、音频合成、3D 建模），本项目将每一个 API 端点都转化为对应的 ComfyUI 节点，让你可以在 ComfyUI 工作流中直接调用 RunningHub 的全部标准模型能力，无需本地 GPU，无冷启动延迟。

## 📌 项目特点

- **完整覆盖** — 110+ 个 ComfyUI 节点，与 [RunningHub 标准模型 API](https://www.runninghub.cn/call-api/standard-api) 一一对应
- **即插即用** — 无需下载模型、无需 GPU，只需 API Key 即可调用全部能力
- **动态注册** — 基于 JSON 注册表自动生成节点，新模型上线后仅需更新注册表
- **多媒体支持** — 图片、视频、音频自动上传 / 下载 / 格式转换，与 ComfyUI 原生类型无缝衔接
- **灵活配置** — 支持节点配置、环境变量、`.env` 文件三种配置方式
- **进度显示** — 任务提交后实时显示轮询进度
- **示例工作流** — 每个节点都附带可直接导入的示例工作流

## 🎨 支持的模型

### 图像生成（20 个节点）

| 模型系列 | 能力 | 节点数 |
|---------|------|--------|
| 全能图片 V1 | 文生图、图生图 | 2 |
| 全能图片 PRO | 文生图、图生图 | 2 |
| 全能图片 PRO 官方 | 文生图、图生图、Ultra | 4 |
| 全能图片 G-1.5 | 文生图、图生图 | 2 |
| Seedream v4 / v4.5 | 文生图、图生图 | 4 |
| 悠船 | 文生图（v6/v61/niji6/niji7/v7）、图生视频 | 6 |

### 视频生成（80 个节点）

| 模型系列 | 能力 | 节点数 |
|---------|------|--------|
| 全能视频 S | 图生视频、文生视频、Pro、官方、角色上传 | 11 |
| 全能视频 V3.1 | Fast/Pro 文生视频、图生视频、首尾帧、参考生视频、视频扩展 | 12 |
| 全能视频 G | 文生视频、图生视频 | 2 |
| 可灵 Kling | v2.5/v2.6/v3.0/o1/o3，文/图/首尾帧/参考/动作控制/编辑 | 20 |
| Vidu | q2/q3，文/图/首尾帧/参考生视频 | 15 |
| 万相 2.6 | 文生视频、图生视频、Flash | 3 |
| 海螺 Hailuo | 02/2.3/2.3-fast，文/图生视频 | 13 |
| Seedance v1.5 | 文/图生视频、Fast、参考生视频 | 5 |

### 音频合成（8 个节点）

| 模型系列 | 能力 | 节点数 |
|---------|------|--------|
| Minimax Speech | 02/2.6/2.8 HD & Turbo | 6 |
| Minimax Music 2.5 | 文生音乐 | 1 |
| Minimax Voice Clone | 声音克隆 | 1 |

### 3D 建模（2 个节点）

| 模型系列 | 能力 | 节点数 |
|---------|------|--------|
| 混元 3D v3.1 | 文生 3D、图生 3D | 2 |

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

## 🚀 使用方法

1. 配置好 API Key（参见上方配置说明）
2. 在 ComfyUI 节点菜单中找到 `RunningHub` 分类
3. 选择你需要的模型节点，连线后运行即可

### 示例工作流

项目在 `examples/` 目录下提供了 110 个示例工作流 JSON 文件，覆盖每一个模型节点。下载后直接导入 ComfyUI 即可使用。

## 📁 项目结构

```
ComfyUI_RH_OpenAPI/
├── __init__.py              # 入口文件，注册所有节点
├── models_registry.json     # 模型注册表（110+ 模型定义）
├── config/
│   └── .env.example         # 配置文件示例
├── core/                    # 核心基础设施
│   ├── base.py              # 节点基类（统一执行流程）
│   ├── api_key.py           # API Key 配置解析
│   ├── upload.py            # 文件上传
│   ├── task.py              # 任务提交与轮询
│   ├── image.py             # 图像工具（Tensor ↔ PIL）
│   ├── video.py             # 视频下载工具
│   └── audio.py             # 音频下载/转换工具
├── nodes/                   # 节点实现
│   ├── settings_node.py     # RH OpenAPI Settings 配置节点
│   └── node_factory.py      # 动态节点工厂
└── examples/                # 110 个示例工作流
```

## 🔧 架构说明

本项目采用 **数据驱动 + 工厂模式** 架构：

1. **模型注册表**（`models_registry.json`）— 以 JSON 格式描述每个模型的端点、参数、输出类型
2. **节点工厂**（`node_factory.py`）— 读取注册表，自动生成 ComfyUI 节点类
3. **统一执行流程**（`core/base.py`）— `准备输入 → 上传媒体 → 提交任务 → 轮询状态 → 处理结果`
4. **媒体工具**（`core/image.py`, `video.py`, `audio.py`）— 负责 ComfyUI 原生类型与 API 之间的格式转换

新增模型只需在注册表中添加一条 JSON 记录，无需编写任何 Python 代码。

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
