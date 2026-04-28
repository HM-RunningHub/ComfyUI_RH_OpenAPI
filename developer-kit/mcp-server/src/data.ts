import { readFileSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import type { ModelDefinition, PublicPricing, PublicRegistry, RunningHubData } from "./types.js";

const __dirname = dirname(fileURLToPath(import.meta.url));
const KIT_ROOT = resolve(__dirname, "../..");

function readJson<T>(path: string): T {
  return JSON.parse(readFileSync(path, "utf-8")) as T;
}

function readText(path: string): string {
  return readFileSync(path, "utf-8");
}

export function loadRunningHubData(kitRoot = KIT_ROOT): RunningHubData {
  const registry = readJson<PublicRegistry>(resolve(kitRoot, "model-registry.public.json"));
  const pricing = readJson<PublicPricing>(resolve(kitRoot, "pricing.public.json"));
  const contract = readText(resolve(kitRoot, "rh-api-contract.md"));
  const llms = readText(resolve(kitRoot, "llms.txt"));

  const modelsByEndpoint = new Map<string, ModelDefinition>();
  for (const model of registry.models) {
    modelsByEndpoint.set(model.endpoint, model);
  }

  const pricingByEndpoint = new Map(pricing.pricing.map((entry) => [entry.endpoint, entry]));

  return {
    registry,
    pricing,
    contract,
    llms,
    modelsByEndpoint,
    pricingByEndpoint,
  };
}

export function getModelOrThrow(data: RunningHubData, endpoint: string): ModelDefinition {
  const model = data.modelsByEndpoint.get(endpoint);
  if (!model) {
    throw new Error(`Unknown RunningHub endpoint: ${endpoint}`);
  }
  return model;
}

export function jsonToolResult(value: unknown) {
  return {
    content: [
      {
        type: "text" as const,
        text: JSON.stringify(value, null, 2),
      },
    ],
  };
}
