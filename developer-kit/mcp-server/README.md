# RunningHub MCP Server

Local MCP server for AI-assisted RunningHub API integration.

This server is for Cursor, Claude Code, Claude Desktop, and other MCP-capable AI
coding tools. It helps AI agents discover RunningHub models, inspect schemas,
estimate public-safe pricing, validate payloads, and build example payloads.

First phase scope is read-only. It does not call the real RunningHub API and
does not require `RH_API_KEY`.

## Tools

- `rh_search_models`  
  Search public RunningHub endpoints by query, output type, media input, and
  price constraints.

- `rh_get_model_schema`  
  Return the exact public schema for one endpoint from
  `model-registry.public.json`.

- `rh_estimate_price`  
  Estimate fixed or parameter-based price from `pricing.public.json`. Prices are
  for integration guidance and must be verified against official RunningHub
  pricing before showing final costs to users.

- `rh_validate_payload`  
  Validate required fields, enum values, scalar types, and media URL fields.

- `rh_get_integration_guide`  
  Return structured integration guidance for auth, upload, submit, poll, retry,
  errors, result parsing, and pricing.

- `rh_build_example_payload`  
  Build a minimal valid payload from a model schema, including media upload
  placeholders.

## Install And Build

```bash
cd developer-kit/mcp-server
npm install
npm run build
npm test
```

## Cursor Configuration

Use the built server with stdio:

```json
{
  "mcpServers": {
    "runninghub": {
      "command": "node",
      "args": [
        "F:/code/ComfyUI_RH_OpenAPI/developer-kit/mcp-server/dist/index.js"
      ]
    }
  }
}
```

For a cloned product repository, update the path to that repo's
`developer-kit/mcp-server/dist/index.js`.

## Example Prompts

Ask the AI agent:

```text
Use the runninghub MCP server. Search for a low-cost text-to-video model that
supports 16:9 output, inspect its schema, build a minimal payload, validate it,
and then show me how to integrate it in my product.
```

```text
Use rh_get_integration_guide before writing code. Do not invent endpoint names,
parameter names, or enum values. Validate the payload with rh_validate_payload.
```

## Design Notes

This MCP server reads local files from the parent `developer-kit` directory:

- `model-registry.public.json`
- `pricing.public.json`
- `rh-api-contract.md`
- `llms.txt`

It intentionally does not implement:

- `rh_upload_media`
- `rh_submit_task`
- `rh_get_task_status`
- `rh_run_model`
- remote deployment
- API key storage

Those belong to a later phase after read-only schema and validation tools are
stable.
