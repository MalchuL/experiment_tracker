/**
 * Serializable attrs for report embed nodes (mirrors Tiptap node attrs).
 * Keep these types framework-agnostic so blocks stay easy to test and reuse.
 */

export interface MetricEmbedAttrs {
  experimentIds: string[];
  /** Empty = show all metric names for selected experiments */
  metricNames: string[];
}

export interface ScalarEmbedAttrs {
  experimentIds: string[];
  /** Scalar series / metric names in the scalars UI */
  scalarKeys: string[];
}

export interface ArtifactEmbedAttrs {
  experimentIds: string[];
  /** Optional filter on artifact display name */
  nameFilter: string;
  /** Optional step filter for step-logged artifacts */
  step: number | null;
}

export const defaultMetricEmbedAttrs = (): MetricEmbedAttrs => ({
  experimentIds: [],
  metricNames: [],
});

export const defaultScalarEmbedAttrs = (): ScalarEmbedAttrs => ({
  experimentIds: [],
  scalarKeys: [],
});

export const defaultArtifactEmbedAttrs = (): ArtifactEmbedAttrs => ({
  experimentIds: [],
  nameFilter: "",
  step: null,
});
