# RunningHub API AI 接入工具包

[English](README.md) | 中文

这个工具包用于帮助开发者在自己的产品中接入 RunningHub API，并让 Cursor、Claude Code、Copilot、ChatGPT 等 AI coding 工具能准确理解接入规则。

它的目标不是把网页文档写得更长，而是给 AI 一个小而严格、可测试、可验证的上下文，避免 AI 猜错 endpoint、参数、状态机或上传流程。

## 包含内容

- `llms.txt`  
  AI agent 应该优先阅读的入口文件，包含 RunningHub API 接入硬规则。

- `rh-api-contract.md`  
  稳定 API 生命周期契约：鉴权、上传、提交、轮询、结果解析、错误处理、重试和日志。

- `capabilities.md`  
  自动生成的全量公开模型能力索引，方便开发者和 AI 快速查找可用 endpoint。

- `model-registry.public.json`  
  自动生成的全量公开模型注册表，包含 endpoint、输出类型、参数、枚举选项、媒体限制和必填标记。内部字段已移除。

- `pricing.public.json`  
  自动生成的公开安全价格摘要。固定价格和参数相关价格会尽量转换成结构化 JSON，不包含内部计费 ID、原始表达式或数据库字段。

- `model-registry.sample.json`  
  小型权威样例，覆盖常见图像和视频模型。适合教学和示例，不代表完整生产覆盖。

- `examples/python/client.py`  
  无第三方依赖的最小 Python 客户端，展示正确的接入生命周期。

- `examples/python/*.py`  
  文生图、图生图、文生视频的最小调用示例。

- `tests/test_contract.py`  
  基于 mock 的契约测试，不会调用真实 RunningHub API。

## 开发者如何使用

把整个目录复制或下载到目标产品仓库中：

```text
my-product/
  rh-api-integration-kit/
    llms.txt
    rh-api-contract.md
    capabilities.md
    model-registry.public.json
    pricing.public.json
    model-registry.sample.json
    examples/
    tests/
```

然后先要求 AI coding agent 阅读工具包，不要立即改代码：

```text
请先阅读 rh-api-integration-kit/llms.txt 和
rh-api-integration-kit/rh-api-contract.md。

你必须遵守 RunningHub API Integration Rules。
不要编造 endpoint、参数名、枚举值或响应结构。
请使用 model-registry.public.json 作为所有可用模型 endpoint 和参数的事实来源。

读完后，先解释你理解的接入流程，不要立即编辑代码。
```

AI 确认流程后，再要求它把示例迁移到目标产品：

```text
请基于 rh-api-integration-kit/examples/python/client.py，
在当前产品中实现 RunningHub client/service。

要求：
1. 从 RH_API_KEY 或产品密钥管理系统读取 API Key。
2. 本地媒体文件必须先上传，再提交模型任务。
3. 提交模型任务并提取 taskId。
4. 轮询 /query，直到 SUCCESS、FAILED 或 CANCEL。
5. 返回 taskId、解析后的输出 URL/text，以及原始响应。
6. 实现后运行 conformance tests。
```

选择模型 endpoint 时，让 AI 先看 `capabilities.md`，再读取 `model-registry.public.json` 中对应模型的精确 schema。

如果需要按成本选择模型，让 AI 读取 `pricing.public.json`。这里的价格用于接入参考和成本感知，可能会变化；对最终用户展示价格前，请核对 RunningHub 官方价格。

## 运行 Python 示例

设置凭证：

```bash
export RH_API_KEY=your-api-key
export RH_API_BASE_URL=https://www.runninghub.cn/openapi/v2
```

运行文生图：

```bash
cd developer-kit/examples/python
python text_to_image.py
```

运行图生图：

```bash
cd developer-kit/examples/python
python image_to_image.py ./input.png
```

运行文生视频：

```bash
cd developer-kit/examples/python
python text_to_video.py
```

## 运行契约测试

测试基于 mock，不需要真实 API Key：

```bash
cd developer-kit
python -m unittest tests/test_contract.py
```

当要求 AI 把客户端迁移到其它产品或语言时，可以把这些测试作为基线。

## 重新生成全量注册表

当源模型目录发生变化时，重新生成公开 AI 文件：

```bash
python developer-kit/scripts/build_public_registry.py
```

该命令会更新：

- `developer-kit/model-registry.public.json`
- `developer-kit/pricing.public.json`
- `developer-kit/capabilities.md`

## 注意事项

- 这个工具包是接入辅助资料，不是完整 SDK。
- `model-registry.public.json` 是本工具包中 endpoint 路径和参数的优先事实来源。
- `pricing.public.json` 可用于成本感知路由、模型比较和预算提示，但不是最终计费依据。
- `model-registry.sample.json` 只是紧凑教学样例。
- 如果缺少模型 schema，AI agent 必须向开发者询问，不能猜。
- 产品业务代码应调用封装后的 client/service，不要在各处重复手写原始 HTTP 请求。
