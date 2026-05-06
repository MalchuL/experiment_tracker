import type { Project, ProjectOwner } from "../types";

/** Normalizes API payload: camelCase keys only (`owner.displayName`, nested `team`). */
export function normalizeProject(raw: unknown): Project {
  const r = raw as Record<string, unknown>;
  const team = r.team as { id?: string; name?: string | null } | null | undefined;
  const ownerRaw = r.owner as Record<string, unknown> | undefined;
  const owner: ProjectOwner = {
    id: String(ownerRaw?.id ?? ""),
    email: String(ownerRaw?.email ?? ""),
    displayName: (ownerRaw?.displayName as string | null | undefined) ?? null,
  };
  const teamId: string | null = team?.id ?? null;
  const teamName: string | null = team?.name ?? null;
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
