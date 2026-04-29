import type { Project, ProjectOwner } from "../types";

/** API may return `team: { id, name }` (nested) or flat `teamId` / `teamName`. */
export function normalizeProject(raw: unknown): Project {
  const r = raw as Record<string, unknown>;
  const team = r.team as { id?: string; name?: string | null } | null | undefined;
  const ownerRaw = r.owner as Record<string, unknown> | undefined;
  const owner: ProjectOwner = {
    id: String(ownerRaw?.id ?? ""),
    email: String(ownerRaw?.email ?? ""),
    displayName:
      (ownerRaw?.displayName as string | null | undefined) ??
      (ownerRaw?.display_name as string | null | undefined) ??
      null,
  };
  const teamId: string | null =
    (r.teamId as string | null | undefined) ?? team?.id ?? null;
  const teamName: string | null =
    (r.teamName as string | null | undefined) ?? team?.name ?? null;
  return {
    ...(r as unknown as Project),
    owner,
    teamId,
    teamName,
  };
}

export function normalizeProjectPage<T extends { data: unknown[] }>(page: T): T {
  return {
    ...page,
    data: (page.data as unknown[]).map((row) => normalizeProject(row)),
  };
}
