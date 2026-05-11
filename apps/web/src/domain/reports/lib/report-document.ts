import type { MetricEmbedAttrs, ScalarEmbedAttrs, ArtifactEmbedAttrs } from "../tiptap/embed-blocks/types";

/** Default empty Tiptap document (aligned with backend mapper). */
export function emptyReportDocument(): Record<string, unknown> {
  return {
    type: "doc",
    content: [{ type: "paragraph" }],
  };
}

export function isMetricEmbedAttrs(value: unknown): value is MetricEmbedAttrs {
  if (!value || typeof value !== "object") {
    return false;
  }
  const o = value as Record<string, unknown>;
  return Array.isArray(o.experimentIds) && Array.isArray(o.metricNames);
}

export function isScalarEmbedAttrs(value: unknown): value is ScalarEmbedAttrs {
  if (!value || typeof value !== "object") {
    return false;
  }
  const o = value as Record<string, unknown>;
  return Array.isArray(o.experimentIds) && Array.isArray(o.scalarKeys);
}

export function isArtifactEmbedAttrs(value: unknown): value is ArtifactEmbedAttrs {
  if (!value || typeof value !== "object") {
    return false;
  }
  const o = value as Record<string, unknown>;
  return (
    Array.isArray(o.experimentIds) &&
    typeof o.nameFilter === "string" &&
    (o.step === null || typeof o.step === "number")
  );
}
