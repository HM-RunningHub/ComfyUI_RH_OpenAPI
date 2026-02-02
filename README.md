# ComfyUI_RH_OpenAPI

ComfyUI 插件，调用 RunningHub OpenAPI 标准模型，支持文生图、图生图、文生视频、图生视频、参考生图、参考生视频等能力。

## 安装

```bash
cd ComfyUI/custom_nodes
git clone https://github.com/HM-RunningHub/ComfyUI_RH_OpenAPI
pip install -r ComfyUI_RH_OpenAPI/requirements.txt
```

## 配置

复制配置示例并编辑：

```bash
cp ComfyUI_RH_OpenAPI/config/.env.example ComfyUI_RH_OpenAPI/config/.env
# 编辑 config/.env，填入 RH_API_KEY
```

或使用 **RH OpenAPI Settings** 节点在画布中配置 base_url 和 apiKey。

## 使用方法

1. 将 **RH OpenAPI Settings** 节点（可选）连接到生成节点，或配置环境变量/config/.env
2. 使用各能力节点（如 RH Banana 图生图）进行生成

## 许可证

Apache-2.0
