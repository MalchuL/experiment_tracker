import type { Experiment } from "@/domain/experiments/types";

export type ExperimentSearchFields = Pick<Experiment, "id" | "name" | "description" | "tags">;

/** Case-insensitive substring match on experiment id, name, description, and tags. */
export function experimentMatchesSearch(
  experiment: ExperimentSearchFields,
  query: string
): boolean {
  const normalized = query.trim().toLowerCase();
  if (!normalized) return true;
  if (experiment.name.toLowerCase().includes(normalized)) return true;
  if (experiment.id.toLowerCase().includes(normalized)) return true;
  if ((experiment.description ?? "").toLowerCase().includes(normalized)) return true;
  if ((experiment.tags ?? []).some((tag) => tag.toLowerCase().includes(normalized))) return true;
  return false;
}
