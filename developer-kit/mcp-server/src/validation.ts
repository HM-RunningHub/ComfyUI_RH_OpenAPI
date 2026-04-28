import type { ModelDefinition, ModelParam } from "./types.js";

const MEDIA_TYPES = new Set(["IMAGE", "VIDEO", "AUDIO"]);

export function validatePayload(model: ModelDefinition, payload: Record<string, unknown>) {
  const errors: string[] = [];
  const warnings: string[] = [];
  const paramsByKey = new Map(model.params.map((param) => [param.fieldKey, param]));

  for (const param of model.params) {
    const value = payload[param.fieldKey];
    if (param.required && isMissing(value)) {
      errors.push(`Missing required parameter: ${param.fieldKey}`);
      continue;
    }
    if (isMissing(value)) {
      continue;
    }
    validateParamValue(param, value, errors);
  }

  for (const key of Object.keys(payload)) {
    if (!paramsByKey.has(key)) {
      warnings.push(`Unknown payload field: ${key}`);
    }
  }

  return {
    valid: errors.length === 0,
    errors,
    warnings,
  };
}

function validateParamValue(param: ModelParam, value: unknown, errors: string[]) {
  switch (param.type) {
    case "LIST": {
      const options = getOptionValues(param);
      if (options.length && !options.includes(String(value))) {
        errors.push(`Invalid enum value for ${param.fieldKey}: ${String(value)}. Allowed: ${options.join(", ")}`);
      }
      break;
    }
    case "BOOLEAN":
      if (typeof value !== "boolean") {
        errors.push(`Invalid boolean for ${param.fieldKey}: expected true/false, got ${typeof value}`);
      }
      break;
    case "INT":
      if (!Number.isInteger(value)) {
        errors.push(`Invalid integer for ${param.fieldKey}: ${String(value)}`);
      }
      break;
    case "FLOAT":
      if (typeof value !== "number" || Number.isNaN(value)) {
        errors.push(`Invalid number for ${param.fieldKey}: ${String(value)}`);
      }
      break;
    case "IMAGE":
    case "VIDEO":
    case "AUDIO":
      validateMediaValue(param, value, errors);
      break;
    case "STRING":
      if (typeof value !== "string") {
        errors.push(`Invalid string for ${param.fieldKey}: got ${typeof value}`);
      }
      break;
    default:
      break;
  }
}

function validateMediaValue(param: ModelParam, value: unknown, errors: string[]) {
  const values = Array.isArray(value) ? value : [value];
  for (const item of values) {
    if (typeof item !== "string") {
      errors.push(`Invalid media URL for ${param.fieldKey}: expected URL string`);
      continue;
    }
    if (!isRemoteUrl(item) && !item.startsWith("asset://")) {
      errors.push(
        `Invalid media value for ${param.fieldKey}: local paths must be uploaded first via /media/upload/binary`,
      );
    }
  }
}

export function isMediaParam(param: ModelParam): boolean {
  return MEDIA_TYPES.has(String(param.type));
}

export function getOptionValues(param: ModelParam): string[] {
  return (param.options || []).map((option) => {
    if (typeof option === "string") {
      return option;
    }
    return String(option.value);
  });
}

export function isMissing(value: unknown): boolean {
  return value === undefined || value === null || value === "";
}

function isRemoteUrl(value: string): boolean {
  return /^https?:\/\//i.test(value);
}
