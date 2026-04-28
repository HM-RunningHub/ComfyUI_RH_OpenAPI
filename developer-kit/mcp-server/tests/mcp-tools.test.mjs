import assert from "node:assert/strict";
import { test } from "node:test";
import { loadRunningHubData } from "../dist/data.js";
import { buildExamplePayload } from "../dist/examplePayload.js";
import { getIntegrationGuide } from "../dist/integrationGuide.js";
import { estimatePrice } from "../dist/pricing.js";
import { searchModels } from "../dist/search.js";
import { createToolHandlers } from "../dist/tools.js";
import { validatePayload } from "../dist/validation.js";

const data = loadRunningHubData();
const handlers = createToolHandlers(data);

function parseToolResult(result) {
  return JSON.parse(result.content[0].text);
}

test("search returns known text-to-image endpoint", () => {
  const result = searchModels(data, { query: "text image banana", output_type: "image", limit: 20 });
  assert.ok(result.models.some((model) => model.endpoint === "rhart-image-v1/text-to-image"));
});

test("schema lookup returns output type and params", () => {
  const model = data.modelsByEndpoint.get("rhart-image-v1/text-to-image");
  assert.ok(model);
  assert.equal(model.output_type, "image");
  assert.ok(model.params.some((param) => param.fieldKey === "prompt"));
});

test("price estimation supports fixed and parameter-based pricing", () => {
  const fixed = estimatePrice(data.pricingByEndpoint.get("rhart-image-v1/text-to-image"), {});
  assert.equal(fixed.estimable, true);
  assert.equal(fixed.price, 0.05);

  const parameterBased = estimatePrice(data.pricingByEndpoint.get("rhart-video-v3.1-fast/text-to-video"), {
    resolution: "720p",
  });
  assert.equal(parameterBased.estimable, true);
  assert.equal(parameterBased.price, 0.2);
});

test("payload validation catches missing required, invalid enum, and local media path", () => {
  const t2i = data.modelsByEndpoint.get("rhart-image-v1/text-to-image");
  assert.ok(t2i);
  assert.equal(validatePayload(t2i, { aspectRatio: "1:1" }).valid, false);
  assert.equal(validatePayload(t2i, { prompt: "cat", aspectRatio: "square" }).valid, false);
  assert.equal(validatePayload(t2i, { prompt: "cat", aspectRatio: "1:1" }).valid, true);

  const i2i = data.modelsByEndpoint.get("rhart-image-v1/edit");
  assert.ok(i2i);
  const localPath = validatePayload(i2i, {
    prompt: "edit",
    aspectRatio: "auto",
    imageUrls: ["./input.png"],
  });
  assert.equal(localPath.valid, false);
  assert.ok(localPath.errors.some((error) => error.includes("uploaded first")));
});

test("example payload is minimal and validates", () => {
  const model = data.modelsByEndpoint.get("rhart-image-v1/text-to-image");
  assert.ok(model);
  const example = buildExamplePayload(model, "minimal");
  assert.equal(example.payload.aspectRatio, "3:4");
  assert.equal(validatePayload(model, example.payload).valid, true);
});

test("integration guide includes async lifecycle", () => {
  const guide = getIntegrationGuide("all");
  assert.ok(guide.lifecycle.includes("Submit task"));
  assert.ok(guide.lifecycle.includes("Poll /query until terminal status"));
});

test("all six MCP tool handlers execute successfully", () => {
  const search = parseToolResult(
    handlers.rh_search_models({ query: "text image banana", output_type: "image", limit: 20 }),
  );
  assert.ok(search.models.some((model) => model.endpoint === "rhart-image-v1/text-to-image"));

  const schema = parseToolResult(
    handlers.rh_get_model_schema({ endpoint: "rhart-image-v1/text-to-image" }),
  );
  assert.equal(schema.output_type, "image");

  const price = parseToolResult(
    handlers.rh_estimate_price({
      endpoint: "rhart-video-v3.1-fast/text-to-video",
      payload: { resolution: "720p" },
    }),
  );
  assert.equal(price.price, 0.2);

  const validation = parseToolResult(
    handlers.rh_validate_payload({
      endpoint: "rhart-image-v1/text-to-image",
      payload: { prompt: "cat", aspectRatio: "1:1" },
    }),
  );
  assert.equal(validation.valid, true);

  const guide = parseToolResult(handlers.rh_get_integration_guide({ topic: "poll" }));
  assert.ok(guide.steps.some((step) => step.includes("/query")));

  const example = parseToolResult(
    handlers.rh_build_example_payload({ endpoint: "rhart-image-v1/text-to-image" }),
  );
  assert.equal(example.payload.aspectRatio, "3:4");
});
