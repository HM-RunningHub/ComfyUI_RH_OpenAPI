# RunningHub API AI Integration Kit

[中文](README_ZH.md) | English

This kit helps developers integrate RunningHub APIs into their own products with
AI coding tools such as Cursor, Claude Code, Copilot, or ChatGPT.

The goal is not to make the web documentation longer. The goal is to give AI
agents a small, strict, testable context so they can generate accurate
integration code without guessing endpoint behavior.

## What Is Included

- `llms.txt`  
  The first file an AI agent should read. It contains hard rules for RunningHub
  API integration.

- `rh-api-contract.md`  
  The stable API lifecycle contract: authentication, upload, submit, poll,
  result parsing, errors, retries, and logging.

- `capabilities.md`  
  A generated human-readable capability index for all public model endpoints in
  this kit.

- `model-registry.public.json`  
  The generated full public model registry for AI agents. It contains endpoint
  paths, output types, parameters, enum options, media limits, and required
  flags. Internal fields such as pricing metadata are removed.

- `pricing.public.json`  
  A generated public-safe pricing summary. It includes fixed prices and
  parameter-based pricing rules when they can be converted into structured JSON.
  It does not include internal billing IDs, raw expressions, or database fields.

- `model-registry.sample.json`  
  A small authoritative schema sample for common image and video models. Use it
  for compact examples, not for complete production coverage.

- `examples/python/client.py`  
  A dependency-free minimal Python client that demonstrates the correct
  integration lifecycle.

- `examples/python/*.py`  
  Minimal examples for text-to-image, image-to-image, and text-to-video.

- `tests/test_contract.py`  
  Mock-based conformance tests. These tests do not call the real RunningHub API.

## How Developers Should Use This Kit

Copy or download this directory into the target product repository:

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

Then ask the AI coding agent to read the kit before making changes:

```text
Please first read rh-api-integration-kit/llms.txt and
rh-api-integration-kit/rh-api-contract.md.

You must follow the RunningHub API Integration Rules.
Do not invent endpoints, parameter names, enum values, or response shapes.
Use model-registry.public.json as the source of truth for all available model
endpoints and parameters.

After reading, explain the integration flow first. Do not edit code yet.
```

After the AI confirms the flow, ask it to implement integration in the host
product:

```text
Based on rh-api-integration-kit/examples/python/client.py, implement a
RunningHub client/service in this product.

Requirements:
1. Read API key from RH_API_KEY or the product's secret manager.
2. Upload local media before submitting model tasks.
3. Submit the model task and extract taskId.
4. Poll /query until SUCCESS, FAILED, or CANCEL.
5. Return taskId, parsed output URLs/text, and raw response.
6. Run the conformance tests after implementation.
```

To choose a model endpoint, ask the AI to inspect `capabilities.md` first, then
read the exact model entry from `model-registry.public.json`.

For cost-aware model selection, ask the AI to read `pricing.public.json`.
Prices in this kit are for integration guidance and may change. Verify official
RunningHub pricing before showing final costs to end users.

## Running the Python Examples

Set credentials:

```bash
export RH_API_KEY=your-api-key
export RH_API_BASE_URL=https://www.runninghub.cn/openapi/v2
```

Run text-to-image:

```bash
cd developer-kit/examples/python
python text_to_image.py
```

Run image-to-image:

```bash
cd developer-kit/examples/python
python image_to_image.py ./input.png
```

Run text-to-video:

```bash
cd developer-kit/examples/python
python text_to_video.py
```

## Running Conformance Tests

The tests are mock-based and do not require real credentials:

```bash
cd developer-kit
python -m unittest tests/test_contract.py
```

Use these tests as a baseline when asking an AI agent to port the client into a
different product or language.

## Regenerating the Full Registry

When the source model catalog changes, regenerate the public AI files:

```bash
python developer-kit/scripts/build_public_registry.py
```

This updates:

- `developer-kit/model-registry.public.json`
- `developer-kit/pricing.public.json`
- `developer-kit/capabilities.md`

## Important Notes

- This kit is an integration aid, not a complete SDK.
- `model-registry.public.json` is the preferred local source of truth for
  endpoint paths and parameters in this kit.
- `pricing.public.json` is useful for cost-aware routing, model comparison, and
  budget hints, but it is not a billing authority.
- `model-registry.sample.json` is only a compact teaching sample.
- The AI agent must ask for missing model schemas instead of guessing.
- Business code should call a client/service wrapper, not duplicate raw HTTP
  requests throughout the product.
