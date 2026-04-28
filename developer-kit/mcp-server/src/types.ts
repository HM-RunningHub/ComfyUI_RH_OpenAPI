export type OutputType = "image" | "video" | "audio" | "3d" | "string";
export type ParamType = "STRING" | "LIST" | "BOOLEAN" | "INT" | "FLOAT" | "IMAGE" | "VIDEO" | "AUDIO";

export interface ModelParam {
  fieldKey: string;
  type: ParamType | string;
  required: boolean;
  label?: string;
  description?: string;
  descriptionEn?: string;
  defaultValue?: unknown;
  options?: Array<{ value: string; description?: string; descriptionEn?: string } | string>;
  multipleInputs?: boolean;
  maxInputNum?: number;
  maxInpuNum?: number;
  accept?: string[] | string;
  maxSize?: number;
  min?: number;
  max?: number;
  step?: number;
  maxLength?: number;
}

export interface ModelDefinition {
  class_name?: string;
  display_name?: string;
  name_cn?: string;
  name_en?: string;
  endpoint: string;
  output_type: OutputType | string;
  category?: string;
  params: ModelParam[];
  asset_ids_mode?: string;
  real_person_asset_slots?: string[];
  real_person_mode_default?: boolean;
}

export interface PublicRegistry {
  version: string;
  source: string;
  model_count: number;
  counts_by_output_type: Record<string, number>;
  counts_by_category: Record<string, number>;
  models: ModelDefinition[];
}

export interface PricingRule {
  when: Record<string, string>;
  price: number;
}

export interface PricingEntry {
  endpoint: string;
  name_cn?: string;
  name_en?: string;
  currency: string;
  unit: string;
  source?: string;
  updated_at?: string;
  pricing_type: "fixed" | "parameter_based" | "unparsed" | string;
  price?: number;
  depends_on?: string[];
  rules?: PricingRule[];
  note?: string;
}

export interface PublicPricing {
  version: string;
  source: string;
  note: string;
  pricing_count: number;
  counts_by_pricing_type: Record<string, number>;
  pricing: PricingEntry[];
}

export interface RunningHubData {
  registry: PublicRegistry;
  pricing: PublicPricing;
  contract: string;
  llms: string;
  modelsByEndpoint: Map<string, ModelDefinition>;
  pricingByEndpoint: Map<string, PricingEntry>;
}

export interface ToolResult {
  content: Array<{ type: "text"; text: string }>;
}
