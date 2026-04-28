import { z } from "zod";
import { getModelOrThrow, jsonToolResult } from "./data.js";
import { buildExamplePayload } from "./examplePayload.js";
import { getIntegrationGuide } from "./integrationGuide.js";
import { estimatePrice } from "./pricing.js";
import { searchModels } from "./search.js";
import type { RunningHubData } from "./types.js";
import { validatePayload } from "./validation.js";

export const searchModelsSchema = {
  query: z.string().optional(),
  output_type: z.enum(["image", "video", "audio", "3d", "string"]).optional(),
  has_media_input: z.boolean().optional(),
  max_price: z.number().optional(),
  limit: z.number().int().min(1).max(50).optional(),
};

export const endpointSchema = {
  endpoint: z.string().min(1),
};

export const estimatePriceSchema = {
  endpoint: z.string().min(1),
  payload: z.record(z.unknown()).optional(),
};

export const validatePayloadSchema = {
  endpoint: z.string().min(1),
  payload: z.record(z.unknown()),
};

export const integrationGuideSchema = {
  topic: z.enum(["all", "auth", "upload", "submit", "poll", "result_parsing", "retry", "errors", "pricing"]).optional(),
};

export const buildExamplePayloadSchema = {
  endpoint: z.string().min(1),
  mode: z.enum(["minimal", "with_optional_defaults"]).optional(),
};

export function createToolHandlers(data: RunningHubData) {
  return {
    rh_search_models: (input: z.infer<z.ZodObject<typeof searchModelsSchema>>) => {
      return jsonToolResult(searchModels(data, input));
    },
    rh_get_model_schema: (input: z.infer<z.ZodObject<typeof endpointSchema>>) => {
      return jsonToolResult(getModelOrThrow(data, input.endpoint));
    },
    rh_estimate_price: (input: z.infer<z.ZodObject<typeof estimatePriceSchema>>) => {
      return jsonToolResult({
        endpoint: input.endpoint,
        ...estimatePrice(data.pricingByEndpoint.get(input.endpoint), input.payload || {}),
      });
    },
    rh_validate_payload: (input: z.infer<z.ZodObject<typeof validatePayloadSchema>>) => {
      const model = getModelOrThrow(data, input.endpoint);
      return jsonToolResult({
        endpoint: input.endpoint,
        ...validatePayload(model, input.payload),
      });
    },
    rh_get_integration_guide: (input: z.infer<z.ZodObject<typeof integrationGuideSchema>>) => {
      return jsonToolResult(getIntegrationGuide(input.topic || "all"));
    },
    rh_build_example_payload: (input: z.infer<z.ZodObject<typeof buildExamplePayloadSchema>>) => {
      const model = getModelOrThrow(data, input.endpoint);
      return jsonToolResult(buildExamplePayload(model, input.mode || "minimal"));
    },
  };
}
