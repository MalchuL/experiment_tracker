/** One row in the by-label metrics pivot (matches API `values[]` + experiment meta). */
export type MetricsTableRow = {
  experimentId: string;
  experimentName: string;
  createdAt: string;
  /** Display color: project experiment color when known, else a chart fallback. */
  experimentColor: string;
  byName: Record<string, number | null>;
};

/** Subset of UI persisted under {@link PERSISTED_UI_KEY_PREFIX}. */
export type PersistedMetricsUi = {
  label?: string;
  includeAll?: boolean;
  columnOrder?: string[];
  columnSizing?: Record<string, number>;
  /** Pin the experiment column (and horizontal lead) inside the metrics grid scrollport. */
  pinLeadColumns?: boolean;
  /** When true (default), experiment names wrap; when false, truncate to one line. */
  wrapExperimentNames?: boolean;
};
