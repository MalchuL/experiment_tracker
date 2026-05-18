/**
 * Shared column width semantics for project data tables (experiments list + metrics pivot).
 *
 * - **fixed**: default pixel width with optional user resize persisted as px.
 * - **auto**: inferred content width between min/max unless the user resized it.
 */

export type ColumnWidthPolicyFixed = {
  mode: "fixed";
  defaultPx: number;
  minPx: number;
  maxPx: number;
};

export type ColumnWidthPolicyAuto = {
  mode: "auto";
  minPx: number;
  maxPx: number;
};

export type ColumnWidthPolicy = ColumnWidthPolicyFixed | ColumnWidthPolicyAuto;

export function isFixedWidthPolicy(p: ColumnWidthPolicy): p is ColumnWidthPolicyFixed {
  return p.mode === "fixed";
}

export function isAutoWidthPolicy(p: ColumnWidthPolicy): p is ColumnWidthPolicyAuto {
  return p.mode === "auto";
}
