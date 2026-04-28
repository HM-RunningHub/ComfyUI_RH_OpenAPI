import type { PricingEntry, PricingRule } from "./types.js";

export function summarizePricing(entry: PricingEntry | undefined): string {
  if (!entry) {
    return "";
  }
  if (entry.pricing_type === "fixed" && typeof entry.price === "number") {
    return `${entry.price} ${entry.currency}${entry.unit}`;
  }
  if (entry.pricing_type === "parameter_based" && entry.rules?.length) {
    const prices = [...new Set(entry.rules.map((rule) => rule.price))].sort((a, b) => a - b);
    const dependsOn = entry.depends_on?.join(",") || "parameters";
    if (prices.length === 1) {
      return `${prices[0]} ${entry.currency}${entry.unit} by ${dependsOn}`;
    }
    return `${prices[0]}-${prices[prices.length - 1]} ${entry.currency}${entry.unit} by ${dependsOn}`;
  }
  return entry.note || "pricing available; see pricing.public.json";
}

export function estimatePrice(entry: PricingEntry | undefined, payload: Record<string, unknown> = {}) {
  if (!entry) {
    return {
      estimable: false,
      reason: "No pricing entry found for this endpoint.",
    };
  }

  if (entry.pricing_type === "fixed" && typeof entry.price === "number") {
    return {
      estimable: true,
      pricing_type: "fixed",
      currency: entry.currency,
      unit: entry.unit,
      price: entry.price,
      note: "Verify official RunningHub pricing before showing final costs to end users.",
    };
  }

  if (entry.pricing_type === "parameter_based") {
    const matchedRule = findMatchingRule(entry.rules || [], payload);
    if (matchedRule) {
      return {
        estimable: true,
        pricing_type: "parameter_based",
        currency: entry.currency,
        unit: entry.unit,
        price: matchedRule.price,
        matched_rule: matchedRule.when,
        note: "Verify official RunningHub pricing before showing final costs to end users.",
      };
    }

    const prices = [...new Set((entry.rules || []).map((rule) => rule.price))].sort((a, b) => a - b);
    return {
      estimable: false,
      pricing_type: "parameter_based",
      currency: entry.currency,
      unit: entry.unit,
      depends_on: entry.depends_on || [],
      price_range: prices.length ? { min: prices[0], max: prices[prices.length - 1] } : undefined,
      reason: "Payload does not contain enough pricing parameters to match a rule.",
      rules: entry.rules || [],
    };
  }

  return {
    estimable: false,
    pricing_type: entry.pricing_type,
    reason: entry.note || "Pricing exists but is not structured enough for estimation.",
  };
}

function findMatchingRule(rules: PricingRule[], payload: Record<string, unknown>): PricingRule | undefined {
  return rules.find((rule) => {
    return Object.entries(rule.when).every(([key, expected]) => {
      const actual = payload[key];
      return actual !== undefined && String(actual) === String(expected);
    });
  });
}
