const GUIDES = {
  auth: {
    steps: ["Use Authorization: Bearer <RH_API_KEY> on every request.", "Never hardcode API keys."],
    must: ["Read credentials from env vars, secret managers, or host product config."],
    must_not: ["Do not log full API keys."],
  },
  upload: {
    steps: [
      "For local image, video, or audio files, call POST /media/upload/binary first.",
      "Use multipart field name file.",
      "Use data.download_url in model payload media fields.",
    ],
    must: ["Upload local media before submit."],
    must_not: ["Do not place local file paths into imageUrl, imageUrls, videoUrl, or audioUrl."],
  },
  submit: {
    steps: ["POST {base_url}/{endpoint} with JSON payload.", "Extract taskId from the submit response."],
    must: ["Endpoint must come from model-registry.public.json."],
    must_not: ["Do not assume submit returns final generated media."],
  },
  poll: {
    steps: [
      "POST {base_url}/query with { taskId }.",
      "Treat CREATE, QUEUED, RUNNING as non-terminal.",
      "Treat SUCCESS as terminal success.",
      "Treat FAILED and CANCEL as terminal failure.",
    ],
    must: ["Use a maximum polling time."],
    must_not: ["Do not poll forever."],
  },
  result_parsing: {
    steps: ["Read media outputs from results[].url or results[].outputUrl.", "Read text outputs from results[].text, content, or output."],
    must: ["Return taskId, parsed outputs, and raw response."],
    must_not: ["Do not discard raw responses needed for debugging."],
  },
  retry: {
    steps: ["Retry network errors, HTTP 429, and HTTP 5xx with backoff."],
    must: ["Keep retry counts bounded."],
    must_not: ["Do not retry invalid parameters, unauthorized requests, insufficient balance, quota, moderation, or policy failures."],
  },
  errors: {
    steps: ["Surface errorCode, errorMessage, taskId, and requestId when available."],
    must: ["Make failures diagnosable."],
    must_not: ["Do not hide taskId on timeout or failure."],
  },
  pricing: {
    steps: ["Use pricing.public.json for cost-aware routing and budget hints."],
    must: ["Verify official RunningHub pricing before showing final costs to end users."],
    must_not: ["Do not treat developer-kit pricing as billing authority."],
  },
};

export type GuideTopic = keyof typeof GUIDES | "all";

export function getIntegrationGuide(topic: GuideTopic = "all") {
  if (topic === "all") {
    return {
      topic,
      guides: GUIDES,
      lifecycle: [
        "Resolve config",
        "Upload local media when needed",
        "Build payload from schema",
        "Submit task",
        "Extract taskId",
        "Poll /query until terminal status",
        "Return outputs and raw response",
      ],
    };
  }
  return {
    topic,
    ...GUIDES[topic],
  };
}
