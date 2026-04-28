#!/usr/bin/env node

import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import { loadRunningHubData } from "./data.js";
import {
  buildExamplePayloadSchema,
  createToolHandlers,
  endpointSchema,
  estimatePriceSchema,
  integrationGuideSchema,
  searchModelsSchema,
  validatePayloadSchema,
} from "./tools.js";

const data = loadRunningHubData();
const handlers = createToolHandlers(data);

const server = new McpServer({
  name: "runninghub-mcp-server",
  version: "0.1.0",
});

server.tool(
  "rh_search_models",
  "Search RunningHub public model endpoints by query, output type, media input, and pricing.",
  searchModelsSchema,
  async (input) => handlers.rh_search_models(input),
);

server.tool(
  "rh_get_model_schema",
  "Return the exact public schema for a RunningHub model endpoint.",
  endpointSchema,
  async (input) => handlers.rh_get_model_schema(input),
);

server.tool(
  "rh_estimate_price",
  "Estimate model price from public-safe pricing rules. Verify official pricing before showing final costs.",
  estimatePriceSchema,
  async (input) => handlers.rh_estimate_price(input),
);

server.tool(
  "rh_validate_payload",
  "Validate a payload against a RunningHub model schema and catch common AI integration mistakes.",
  validatePayloadSchema,
  async (input) => handlers.rh_validate_payload(input),
);

server.tool(
  "rh_get_integration_guide",
  "Return structured RunningHub API integration guidance for auth, upload, submit, poll, retry, errors, and pricing.",
  integrationGuideSchema,
  async (input) => handlers.rh_get_integration_guide(input),
);

server.tool(
  "rh_build_example_payload",
  "Build a minimal valid example payload for a RunningHub endpoint from its public schema.",
  buildExamplePayloadSchema,
  async (input) => handlers.rh_build_example_payload(input),
);

const transport = new StdioServerTransport();
await server.connect(transport);
