# RunningHub API Contract

This document describes the stable integration contract that AI coding agents
and developers should follow when integrating RunningHub APIs into a product.

## Base URL

Default base URL:

```text
https://www.runninghub.cn/openapi/v2
```

Every endpoint in the model registry is relative to this base URL.

Example:

```text
endpoint: rhart-image-v1/text-to-image
url: https://www.runninghub.cn/openapi/v2/rhart-image-v1/text-to-image
```

## Authentication

Every API request must include:

```text
Authorization: Bearer <RH_API_KEY>
```

JSON requests must also include:

```text
Content-Type: application/json
```

Never hardcode the API key. Prefer `RH_API_KEY` and optionally
`RH_API_BASE_URL` environment variables for examples and local development.

## File Upload

Local media files must be uploaded before they are used in model payloads.

```http
POST {base_url}/media/upload/binary
Authorization: Bearer <RH_API_KEY>
Content-Type: multipart/form-data
```

The multipart field name is:

```text
file
```

Expected successful upload response shape:

```json
{
  "code": 0,
  "data": {
    "download_url": "https://..."
  }
}
```

Use `data.download_url` as the value for model payload fields such as
`imageUrl`, `imageUrls`, `videoUrl`, `videoUrls`, `audioUrl`, or `audioUrls`.

## Submit Task

Submit a model task with:

```http
POST {base_url}/{endpoint}
Authorization: Bearer <RH_API_KEY>
Content-Type: application/json
```

Example request:

```json
{
  "prompt": "A cinematic cat",
  "aspectRatio": "1:1"
}
```

Expected successful submit response:

```json
{
  "taskId": "..."
}
```

Some implementations may also return `task_id`. A robust client may accept both,
but should normalize the value to `task_id` or `taskId` internally.

## Poll Task

Poll task status with:

```http
POST {base_url}/query
Authorization: Bearer <RH_API_KEY>
Content-Type: application/json
```

Request body:

```json
{
  "taskId": "..."
}
```

Known status values:

| Status | Meaning | Terminal |
| --- | --- | --- |
| `CREATE` | Task created | No |
| `QUEUED` | Waiting in queue | No |
| `RUNNING` | Running | No |
| `SUCCESS` | Finished successfully | Yes |
| `FAILED` | Failed | Yes |
| `CANCEL` | Cancelled | Yes |

Polling requirements:

- Use a polling interval, for example 5 seconds.
- Use a maximum polling time, for example 10 to 30 minutes depending on the
  product and model type.
- Never poll forever.
- Return the `taskId` when timeout happens so the developer can inspect the task
  later in RunningHub call records.

## Result Parsing

Expected successful final response:

```json
{
  "status": "SUCCESS",
  "results": [
    {
      "url": "https://...",
      "outputType": "image"
    }
  ]
}
```

Robust clients should read result values from these fields in order:

- URL outputs: `url`, `outputUrl`
- Text outputs: `text`, `content`, `output`

Return both parsed outputs and the raw final response.

Recommended result object:

```json
{
  "task_id": "...",
  "outputs": ["https://..."],
  "raw_response": {}
}
```

## Parameter Rules

Use the model registry or official schema as the source of truth.

- `STRING`: send strings.
- `LIST`: send exactly one of the declared option values.
- `BOOLEAN`: send JSON booleans, not `"true"` or `"false"`.
- `INT`: send JSON integers.
- `FLOAT`: send JSON numbers.
- `IMAGE`, `VIDEO`, `AUDIO`: upload local files first, then send URLs.
- Required parameters must be present.
- Optional empty strings should usually be omitted unless the model schema says
  otherwise.
- Do not invent defaults. Use schema defaults or ask the developer.

## Retry Rules

Retry transient failures:

- Network errors
- HTTP 429
- HTTP 5xx
- Temporary invalid JSON or empty response from a transient network failure

Do not retry deterministic failures:

- HTTP 400 invalid parameter
- HTTP 401 or 403 unauthorized
- Insufficient balance or quota
- Content policy, moderation, NSFW, violation, or forbidden content
- Unknown endpoint
- Missing required parameter

Recommended retry strategy:

- Submit: up to 3 attempts with exponential backoff.
- Upload: up to 3 attempts with exponential backoff.
- Polling: tolerate a small number of consecutive transient poll failures, then
  fail with `taskId`.

## Logging and Security

Logs should include:

- endpoint
- taskId
- status transitions
- sanitized payload preview
- requestId or traceId when available

Logs must not include:

- full API keys
- cookies
- secret tokens
- private file contents

## AI Agent Checklist

Before writing code:

- Read `llms.txt`.
- Read this contract.
- Read the selected model schema.
- Confirm the endpoint and required parameters.

Before finishing:

- Validate auth header creation.
- Validate upload-before-submit for local media.
- Validate task polling status handling.
- Validate timeout behavior.
- Validate no invented enum values.
- Run `tests/test_contract.py` when Python is available.
