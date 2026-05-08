import type { CategoryCleanupErrorEntry, CategoryCleanupResponse } from "@/domain/experiments/types";

export function formatSatelliteLine(
  label: string,
  step: { ok: boolean; skipped?: boolean; errorMessage?: string | null },
): string {
  if (step.skipped) return `${label}: skipped (not configured)`;
  if (step.ok) return `${label}: OK`;
  return `${label}: failed${step.errorMessage ? ` — ${step.errorMessage}` : ""}`;
}

export function formatCategoryCleanupErrors(errors: CategoryCleanupErrorEntry[]): string {
  return errors.map((e) => `${e.category}: ${e.error}`).join("\n");
}

function formatDeletionResultLine(category: string, result: Record<string, unknown>): string {
  if (typeof result.ok === "boolean") {
    return formatSatelliteLine(category, {
      ok: result.ok,
      skipped: Boolean(result.skipped),
      errorMessage: null,
    });
  }
  if (result.deleted === true) {
    const id = typeof result.id === "string" ? result.id : undefined;
    return id ? `${category}: deleted (${id.slice(0, 8)}…)` : `${category}: deleted`;
  }
  return `${category}: ${JSON.stringify(result)}`;
}

const MAX_DELETION_RESULT_LINES = 40;

/** Human-readable summary for cleanup-shaped delete responses (experiment / project / team / user). */
export function formatDeletionOutcomeDescription(out: CategoryCleanupResponse): string {
  const lines: string[] = [];
  if (out.results.length > 0) {
    lines.push("Steps:");
    const slice = out.results.slice(0, MAX_DELETION_RESULT_LINES);
    for (const r of slice) {
      lines.push(`  ${formatDeletionResultLine(r.category, r.result)}`);
    }
    const rest = out.results.length - slice.length;
    if (rest > 0) lines.push(`  …and ${rest} more`);
  }
  if (out.errors.length > 0) {
    lines.push("Failures:");
    lines.push(formatCategoryCleanupErrors(out.errors));
  }
  return lines.join("\n").trim() || "No details.";
}
