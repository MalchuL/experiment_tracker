"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { API_ROUTES } from "@/lib/constants/api-routes";
import { FRONTEND_ROUTES } from "@/lib/constants/frontend-routes";
import { getPublicApiBaseUrl } from "@/lib/runtime-config";
import { Button } from "@/components/ui/button";
import Link from "next/link";
import { Input } from "@/components/ui/input";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import type { CategoryCleanupResponse } from "@/domain/experiments/types";
import { formatDeletionOutcomeDescription } from "@/lib/format-satellite-toast";
import { useToast } from "@/lib/hooks/use-toast";

const STORAGE_KEY = "experiment_tracker_admin_panel_key";

const PAGE_SIZE_OPTIONS = [10, 20, 50] as const;

type AdminUserRow = {
  id: string;
  email: string;
  displayName: string | null;
  isActive: boolean;
  isSuperuser: boolean;
  createdAt: string | null;
};

type AdminTeamRow = {
  id: string;
  name: string;
  description: string | null;
  ownerId: string | null;
  createdAt: string | null;
};

type AdminProjectRow = {
  id: string;
  name: string;
  ownerId: string | null;
  ownerEmail: string | null;
  teamId: string | null;
  teamName: string | null;
};

type AdminPaginated<T> = {
  items: T[];
  total: number;
  limit: number;
  offset: number;
};

type UserDraft = {
  email: string;
  displayName: string;
  isActive: boolean;
  isSuperuser: boolean;
};

function draftFromUser(u: AdminUserRow): UserDraft {
  return {
    email: u.email,
    displayName: u.displayName ?? "",
    isActive: u.isActive,
    isSuperuser: u.isSuperuser,
  };
}

function draftsEqual(a: UserDraft, b: UserDraft): boolean {
  return (
    a.email === b.email &&
    a.displayName === b.displayName &&
    a.isActive === b.isActive &&
    a.isSuperuser === b.isSuperuser
  );
}

const ROW_SELECT_CLASS =
  "border-input bg-background h-9 w-full min-w-[5.5rem] rounded-md border px-2 text-sm";

function adminBaseUrl() {
  return getPublicApiBaseUrl();
}

type AdminFetchOptions = {
  /** When set, use this value for the X-Admin-Key header instead of sessionStorage (e.g. pre-unlock probe). */
  adminKey?: string | null;
};

async function adminFetch(
  pathWithQuery: string,
  init?: RequestInit,
  options?: AdminFetchOptions,
) {
  const key =
    options?.adminKey !== undefined
      ? options.adminKey
      : typeof window !== "undefined"
        ? sessionStorage.getItem(STORAGE_KEY)
        : null;
  const url = `${adminBaseUrl()}/${pathWithQuery.replace(/^\//, "")}`;
  const headers = new Headers(init?.headers);
  if (!headers.has("Content-Type") && init?.body) {
    headers.set("Content-Type", "application/json");
  }
  if (key) {
    headers.set("X-Admin-Key", key);
  }
  return fetch(url, { ...init, headers });
}

async function adminErrorMessage(response: Response): Promise<string> {
  const text = await response.text();
  if (!text) return `${response.status} ${response.statusText}`.trim();
  try {
    const body = JSON.parse(text) as { detail?: unknown };
    if (typeof body.detail === "string") return body.detail;
    if (body.detail) return JSON.stringify(body.detail);
  } catch {
    return text;
  }
  return text;
}

async function probeAdminKey(adminKey: string): Promise<boolean> {
  const r = await adminFetch(
    `${API_ROUTES.ADMIN.USERS}?limit=1&offset=0`,
    undefined,
    { adminKey },
  );
  return r.ok;
}

export default function AdminPage() {
  const { toast } = useToast();
  const [keyInput, setKeyInput] = useState("");
  const [unlocked, setUnlocked] = useState(false);
  const [search, setSearch] = useState("");
  const [teamSearch, setTeamSearch] = useState("");
  const [projectSearch, setProjectSearch] = useState("");
  const [userPageSize, setUserPageSize] = useState<(typeof PAGE_SIZE_OPTIONS)[number]>(20);
  const [teamPageSize, setTeamPageSize] = useState<(typeof PAGE_SIZE_OPTIONS)[number]>(20);
  const [projectPageSize, setProjectPageSize] = useState<(typeof PAGE_SIZE_OPTIONS)[number]>(20);
  const [userOffset, setUserOffset] = useState(0);
  const [teamOffset, setTeamOffset] = useState(0);
  const [projectOffset, setProjectOffset] = useState(0);
  const [users, setUsers] = useState<AdminUserRow[]>([]);
  const [teams, setTeams] = useState<AdminTeamRow[]>([]);
  const [projects, setProjects] = useState<AdminProjectRow[]>([]);
  const [userTotal, setUserTotal] = useState(0);
  const [teamTotal, setTeamTotal] = useState(0);
  const [projectTotal, setProjectTotal] = useState(0);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [resetResult, setResetResult] = useState<{ email: string; password: string } | null>(null);
  const [unlockError, setUnlockError] = useState<string | null>(null);
  const [unlocking, setUnlocking] = useState(false);
  const [userDrafts, setUserDrafts] = useState<Record<string, UserDraft>>({});
  const [savingUserId, setSavingUserId] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    const k = sessionStorage.getItem(STORAGE_KEY);
    if (!k) return;
    void (async () => {
      const ok = await probeAdminKey(k);
      if (cancelled) return;
      if (ok) {
        setUnlocked(true);
      } else {
        sessionStorage.removeItem(STORAGE_KEY);
        setUnlockError("Stored admin key was rejected. Enter a valid key.");
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  const invalidateAdminSession = useCallback((message: string) => {
    sessionStorage.removeItem(STORAGE_KEY);
    setUnlocked(false);
    setUsers([]);
    setTeams([]);
    setProjects([]);
    setUserOffset(0);
    setTeamOffset(0);
    setProjectOffset(0);
    setUserTotal(0);
    setTeamTotal(0);
    setProjectTotal(0);
    setResetResult(null);
    setLoadError(null);
    setUnlockError(message);
    setUserDrafts({});
    setSavingUserId(null);
  }, []);

  const tryUnlock = useCallback(async () => {
    const candidate = keyInput.trim();
    if (!candidate) return;
    setUnlockError(null);
    setUnlocking(true);
    try {
      const ok = await probeAdminKey(candidate);
      if (ok) {
        sessionStorage.setItem(STORAGE_KEY, candidate);
        setUnlocked(true);
        setKeyInput("");
        setLoadError(null);
      } else {
        setUnlockError("Invalid admin key.");
      }
    } finally {
      setUnlocking(false);
    }
  }, [keyInput]);

  const lock = () => {
    sessionStorage.removeItem(STORAGE_KEY);
    setUnlocked(false);
    setUsers([]);
    setTeams([]);
    setProjects([]);
    setUserOffset(0);
    setTeamOffset(0);
    setProjectOffset(0);
    setUserTotal(0);
    setTeamTotal(0);
    setProjectTotal(0);
    setResetResult(null);
    setUnlockError(null);
    setLoadError(null);
    setUserDrafts({});
    setSavingUserId(null);
  };

  const loadTeams = useCallback(
    async (q: string, offset: number, limit: number) => {
      const qs = new URLSearchParams();
      qs.set("limit", String(limit));
      qs.set("offset", String(offset));
      if (q.trim()) qs.set("q", q.trim());
      const r = await adminFetch(`${API_ROUTES.ADMIN.TEAMS}?${qs.toString()}`);
      if (r.status === 403) {
        invalidateAdminSession("Admin key was rejected. Unlock again.");
        return;
      }
      if (!r.ok) {
        setLoadError(await adminErrorMessage(r));
        return;
      }
      setLoadError(null);
      const body = (await r.json()) as AdminPaginated<AdminTeamRow>;
      setTeams(body.items ?? []);
      setTeamTotal(body.total ?? 0);
    },
    [invalidateAdminSession],
  );

  const loadUsers = useCallback(
    async (q: string, offset: number, limit: number) => {
      const qs = new URLSearchParams();
      qs.set("limit", String(limit));
      qs.set("offset", String(offset));
      if (q.trim()) qs.set("q", q.trim());
      const r = await adminFetch(`${API_ROUTES.ADMIN.USERS}?${qs.toString()}`);
      if (r.status === 403) {
        invalidateAdminSession("Admin key was rejected. Unlock again.");
        return;
      }
      if (!r.ok) {
        setLoadError(await adminErrorMessage(r));
        return;
      }
      setLoadError(null);
      const body = (await r.json()) as AdminPaginated<AdminUserRow>;
      const items = body.items ?? [];
      setUsers(items);
      setUserTotal(body.total ?? 0);
      setUserDrafts(Object.fromEntries(items.map((u) => [u.id, draftFromUser(u)])));
    },
    [invalidateAdminSession],
  );

  const loadProjects = useCallback(
    async (q: string, offset: number, limit: number) => {
      const qs = new URLSearchParams();
      qs.set("limit", String(limit));
      qs.set("offset", String(offset));
      if (q.trim()) qs.set("q", q.trim());
      const r = await adminFetch(`${API_ROUTES.ADMIN.PROJECTS}?${qs.toString()}`);
      if (r.status === 403) {
        invalidateAdminSession("Admin key was rejected. Unlock again.");
        return;
      }
      if (!r.ok) {
        setLoadError(await adminErrorMessage(r));
        return;
      }
      const body = (await r.json()) as AdminPaginated<AdminProjectRow>;
      setProjects(body.items ?? []);
      setProjectTotal(body.total ?? 0);
    },
    [invalidateAdminSession],
  );

  const updateUserDraft = useCallback((userId: string, patch: Partial<UserDraft>) => {
    setUserDrafts((prev) => {
      const current = prev[userId];
      if (!current) return prev;
      return { ...prev, [userId]: { ...current, ...patch } };
    });
  }, []);

  useEffect(() => {
    if (!unlocked) return;
    const t = setTimeout(() => {
      setUserOffset(0);
      void loadUsers(search, 0, userPageSize);
    }, 300);
    return () => clearTimeout(t);
  }, [unlocked, search, loadUsers, userPageSize]);

  useEffect(() => {
    if (!unlocked) return;
    const t = setTimeout(() => {
      setTeamOffset(0);
      void loadTeams(teamSearch, 0, teamPageSize);
    }, 300);
    return () => clearTimeout(t);
  }, [unlocked, teamSearch, loadTeams, teamPageSize]);

  useEffect(() => {
    if (!unlocked) return;
    const t = setTimeout(() => {
      setProjectOffset(0);
      void loadProjects(projectSearch, 0, projectPageSize);
    }, 300);
    return () => clearTimeout(t);
  }, [unlocked, projectSearch, loadProjects, projectPageSize]);

  const userHasPrev = userOffset > 0;
  const userHasNext = userOffset + users.length < userTotal;

  const teamHasPrev = teamOffset > 0;
  const teamHasNext = teamOffset + teams.length < teamTotal;
  const projectHasPrev = projectOffset > 0;
  const projectHasNext = projectOffset + projects.length < projectTotal;

  const goPrevUsers = () => {
    const nextOffset = Math.max(0, userOffset - userPageSize);
    setUserOffset(nextOffset);
    void loadUsers(search, nextOffset, userPageSize);
  };

  const goNextUsers = () => {
    const nextOffset = userOffset + userPageSize;
    setUserOffset(nextOffset);
    void loadUsers(search, nextOffset, userPageSize);
  };

  const goPrevTeams = () => {
    const nextOffset = Math.max(0, teamOffset - teamPageSize);
    setTeamOffset(nextOffset);
    void loadTeams(teamSearch, nextOffset, teamPageSize);
  };

  const goNextTeams = () => {
    const nextOffset = teamOffset + teamPageSize;
    setTeamOffset(nextOffset);
    void loadTeams(teamSearch, nextOffset, teamPageSize);
  };

  const goPrevProjects = () => {
    const nextOffset = Math.max(0, projectOffset - projectPageSize);
    setProjectOffset(nextOffset);
    void loadProjects(projectSearch, nextOffset, projectPageSize);
  };

  const goNextProjects = () => {
    const nextOffset = projectOffset + projectPageSize;
    setProjectOffset(nextOffset);
    void loadProjects(projectSearch, nextOffset, projectPageSize);
  };

  const resolveAdminOwner = async (value: string): Promise<string | null> => {
    const target = value.trim();
    if (!target) return null;
    if (!target.includes("@")) return target;
    const r = await adminFetch(`${API_ROUTES.ADMIN.USERS}?q=${encodeURIComponent(target)}&limit=20&offset=0`);
    if (!r.ok) {
      setLoadError(await adminErrorMessage(r));
      return null;
    }
    const body = (await r.json()) as AdminPaginated<AdminUserRow>;
    return body.items.find((user) => user.email.toLowerCase() === target.toLowerCase())?.id ?? null;
  };

  const onChangeProjectTeam = async (project: AdminProjectRow) => {
    const teamId = window.prompt(
      "Enter destination team UUID, or leave empty to make the project standalone.",
      project.teamId ?? "",
    );
    if (teamId === null) return;
    let ownerId: string | null = null;
    if (!teamId.trim() && !project.ownerId) {
      const ownerTarget = window.prompt("This project has no owner. Enter an active owner email or UUID.");
      if (ownerTarget === null) return;
      ownerId = await resolveAdminOwner(ownerTarget);
      if (!ownerId) {
        setLoadError("Active owner was not found.");
        return;
      }
    }
    if (!window.confirm("Change this project's team? Inherited access will change immediately.")) return;
    const r = await adminFetch(API_ROUTES.ADMIN.PROJECT_TEAM(project.id), {
      method: "PATCH",
      body: JSON.stringify({ teamId: teamId.trim() || null, ownerId }),
    });
    if (!r.ok) {
      setLoadError(await adminErrorMessage(r));
      return;
    }
    toast({ title: "Project team changed", description: project.name });
    void loadProjects(projectSearch, projectOffset, projectPageSize);
  };

  const onChangeProjectOwner = async (project: AdminProjectRow) => {
    const ownerTarget = window.prompt("Enter the new owner email or UUID.");
    if (ownerTarget === null) return;
    const ownerId = await resolveAdminOwner(ownerTarget);
    if (!ownerId) {
      setLoadError("Active owner was not found.");
      return;
    }
    if (!window.confirm("Transfer ownership of this standalone project?")) return;
    const r = await adminFetch(API_ROUTES.ADMIN.PROJECT_OWNER(project.id), {
      method: "PATCH",
      body: JSON.stringify({ ownerId }),
    });
    if (!r.ok) {
      setLoadError(await adminErrorMessage(r));
      return;
    }
    toast({ title: "Project owner changed", description: project.name });
    void loadProjects(projectSearch, projectOffset, projectPageSize);
  };

  const onReset = async (userId: string, email: string) => {
    if (
      !window.confirm(
        `Reset password for ${email}? The current password will stop working and a new temporary password will be shown once.`,
      )
    ) {
      return;
    }
    setResetResult(null);
    const r = await adminFetch(API_ROUTES.ADMIN.RESET_PASSWORD(userId), { method: "POST" });
    if (r.status === 403) {
      invalidateAdminSession("Admin key was rejected. Unlock again.");
      return;
    }
    if (!r.ok) {
      setLoadError(await adminErrorMessage(r));
      return;
    }
    const body = (await r.json()) as { temporaryPassword: string };
    setResetResult({ email, password: body.temporaryPassword });
    void loadUsers(search, userOffset, userPageSize);
  };

  const onSaveUser = async (user: AdminUserRow) => {
    const draft = userDrafts[user.id];
    if (!draft) return;
    setSavingUserId(user.id);
    setLoadError(null);
    try {
      const r = await adminFetch(API_ROUTES.ADMIN.UPDATE_USER(user.id), {
        method: "PATCH",
        body: JSON.stringify({
          email: draft.email.trim(),
          displayName: draft.displayName.trim() || null,
          isActive: draft.isActive,
          isSuperuser: draft.isSuperuser,
        }),
      });
      if (r.status === 403) {
        invalidateAdminSession("Admin key was rejected. Unlock again.");
        return;
      }
      if (!r.ok) {
        setLoadError(await adminErrorMessage(r));
        return;
      }
      toast({ title: "User saved", description: user.email });
      void loadUsers(search, userOffset, userPageSize);
    } finally {
      setSavingUserId(null);
    }
  };

  const onDeleteUser = async (userId: string) => {
    if (!window.confirm("Delete this inactive user and personal projects?")) return;
    const r = await adminFetch(API_ROUTES.ADMIN.DELETE_USER(userId), { method: "DELETE" });
    if (!r.ok) {
      setLoadError(await adminErrorMessage(r));
      return;
    }
    const body = (await r.json()) as CategoryCleanupResponse;
    toast({
      title: body.success ? "User deleted" : "User deleted (warnings)",
      description: body.success
        ? "No errors reported for personal projects."
        : formatDeletionOutcomeDescription(body),
      variant: body.success ? "default" : "destructive",
    });
    void loadUsers(search, userOffset, userPageSize);
  };

  const hint = useMemo(
    () =>
      "Enter the backend admin key (header X-Admin-Key). Default in dev is often admin — see server startup warning.",
    [],
  );

  if (!unlocked) {
    return (
      <div className="mx-auto flex min-h-screen max-w-md flex-col justify-center gap-4 p-6">
        <Card>
          <CardHeader>
            <CardTitle>Admin panel</CardTitle>
            <CardDescription>{hint}</CardDescription>
          </CardHeader>
          <CardContent>
            <form
              className="flex flex-col gap-3"
              onSubmit={(e) => {
                e.preventDefault();
                if (!keyInput.trim() || unlocking) return;
                void tryUnlock();
              }}
            >
              {unlockError && (
                <p className="text-sm text-destructive" role="alert">
                  {unlockError}
                </p>
              )}
              <Input
                type="password"
                name="admin-panel-key"
                autoComplete="off"
                placeholder="Admin key"
                value={keyInput}
                disabled={unlocking}
                onChange={(e) => {
                  setKeyInput(e.target.value);
                  if (unlockError) setUnlockError(null);
                }}
              />
              <Button type="submit" disabled={!keyInput.trim() || unlocking}>
                {unlocking ? "Checking…" : "Unlock"}
              </Button>
            </form>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-7xl space-y-8 p-6">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h1 className="text-2xl font-semibold tracking-tight">Admin</h1>
        <Button variant="outline" onClick={lock}>
          Lock / clear key
        </Button>
        <Button asChild variant="outline">
          <Link href={FRONTEND_ROUTES.ADMIN_STORAGE}>Storage Management</Link>
        </Button>
      </div>

      {loadError && (
        <p className="text-sm text-destructive" role="alert">
          {loadError}
        </p>
      )}

      {resetResult && (
        <Card className="border-primary/40 bg-muted/40">
          <CardHeader>
            <CardTitle className="text-base">Temporary password</CardTitle>
            <CardDescription>
              User {resetResult.email} — copy now; it is not stored after you leave this view.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <code className="break-all rounded bg-background px-2 py-1 text-sm">
              {resetResult.password}
            </code>
          </CardContent>
        </Card>
      )}

      <Card>
        <CardHeader>
          <CardTitle>Users</CardTitle>
          <CardDescription>
            Search by email, display name, or user UUID. Edit fields in each row and click Save. Reset
            password and delete are separate actions.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex flex-wrap items-center gap-3">
            <Input
              className="max-w-md flex-1"
              placeholder="Search by email, name, or UUID…"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
            />
            <label className="flex items-center gap-2 text-sm text-muted-foreground">
              <span>Page size</span>
              <select
                className="border-input bg-background h-9 rounded-md border px-2"
                value={userPageSize}
                onChange={(e) => {
                  const v = Number(e.target.value) as (typeof PAGE_SIZE_OPTIONS)[number];
                  setUserPageSize(v);
                  setUserOffset(0);
                }}
              >
                {PAGE_SIZE_OPTIONS.map((n) => (
                  <option key={n} value={n}>
                    {n}
                  </option>
                ))}
              </select>
            </label>
          </div>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead className="w-[280px] min-w-[200px]">UUID</TableHead>
                <TableHead>Email</TableHead>
                <TableHead>Display name</TableHead>
                <TableHead className="min-w-[7rem]">Active</TableHead>
                <TableHead className="min-w-[7rem]">Superuser</TableHead>
                <TableHead className="min-w-[12rem]">Actions</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {users.map((u) => {
                const draft = userDrafts[u.id] ?? draftFromUser(u);
                const saved = draftFromUser(u);
                const dirty = !draftsEqual(draft, saved);
                const saving = savingUserId === u.id;
                return (
                  <TableRow key={u.id}>
                    <TableCell className="font-mono text-xs break-all text-muted-foreground align-top">
                      {u.id}
                    </TableCell>
                    <TableCell className="align-top">
                      <Input
                        type="email"
                        className="min-w-[12rem]"
                        value={draft.email}
                        disabled={saving}
                        onChange={(e) => updateUserDraft(u.id, { email: e.target.value })}
                      />
                    </TableCell>
                    <TableCell className="align-top">
                      <Input
                        className="min-w-[10rem]"
                        placeholder="Display name"
                        value={draft.displayName}
                        disabled={saving}
                        onChange={(e) => updateUserDraft(u.id, { displayName: e.target.value })}
                      />
                    </TableCell>
                    <TableCell className="align-top">
                      <select
                        className={ROW_SELECT_CLASS}
                        value={draft.isActive ? "yes" : "no"}
                        disabled={saving}
                        aria-label={`Active status for ${u.email}`}
                        onChange={(e) =>
                          updateUserDraft(u.id, { isActive: e.target.value === "yes" })
                        }
                      >
                        <option value="yes">Yes</option>
                        <option value="no">No</option>
                      </select>
                    </TableCell>
                    <TableCell className="align-top">
                      <select
                        className={ROW_SELECT_CLASS}
                        value={draft.isSuperuser ? "yes" : "no"}
                        disabled={saving}
                        aria-label={`Superuser status for ${u.email}`}
                        onChange={(e) =>
                          updateUserDraft(u.id, { isSuperuser: e.target.value === "yes" })
                        }
                      >
                        <option value="yes">Yes</option>
                        <option value="no">No</option>
                      </select>
                    </TableCell>
                    <TableCell className="align-top">
                      <div className="flex flex-wrap gap-2">
                        <Button
                          type="button"
                          size="sm"
                          disabled={!dirty || saving}
                          onClick={() => void onSaveUser(u)}
                        >
                          {saving ? "Saving…" : "Save"}
                        </Button>
                        <Button
                          type="button"
                          variant="secondary"
                          size="sm"
                          disabled={saving}
                          onClick={() => void onReset(u.id, u.email)}
                        >
                          Reset password
                        </Button>
                        <Button
                          type="button"
                          variant="destructive"
                          size="sm"
                          disabled={draft.isActive || saving}
                          onClick={() => void onDeleteUser(u.id)}
                        >
                          Delete
                        </Button>
                      </div>
                    </TableCell>
                  </TableRow>
                );
              })}
            </TableBody>
          </Table>
          <div className="flex flex-col gap-2 border-t pt-4 sm:flex-row sm:items-center sm:justify-between">
            <p className="text-xs text-muted-foreground">
              {userTotal === 0
                ? "No users match"
                : `Showing ${userOffset + 1}–${userOffset + users.length} of ${userTotal}`}
            </p>
            <div className="flex gap-2">
              <Button type="button" variant="outline" size="sm" disabled={!userHasPrev} onClick={goPrevUsers}>
                Previous
              </Button>
              <Button type="button" variant="outline" size="sm" disabled={!userHasNext} onClick={goNextUsers}>
                Next
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Projects</CardTitle>
          <CardDescription>
            Search projects and repair team assignment or standalone ownership.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex flex-wrap items-center gap-3">
            <Input
              className="max-w-md flex-1"
              placeholder="Search projects…"
              value={projectSearch}
              onChange={(e) => setProjectSearch(e.target.value)}
            />
            <label className="flex items-center gap-2 text-sm text-muted-foreground">
              <span>Page size</span>
              <select
                className="border-input bg-background h-9 rounded-md border px-2"
                value={projectPageSize}
                onChange={(e) => {
                  const v = Number(e.target.value) as (typeof PAGE_SIZE_OPTIONS)[number];
                  setProjectPageSize(v);
                  setProjectOffset(0);
                }}
              >
                {PAGE_SIZE_OPTIONS.map((n) => (
                  <option key={n} value={n}>{n}</option>
                ))}
              </select>
            </label>
          </div>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Name</TableHead>
                <TableHead>Project id</TableHead>
                <TableHead>Owner</TableHead>
                <TableHead>Team</TableHead>
                <TableHead>Actions</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {projects.map((project) => (
                <TableRow key={project.id}>
                  <TableCell>{project.name}</TableCell>
                  <TableCell className="font-mono text-xs">{project.id}</TableCell>
                  <TableCell>{project.ownerEmail ?? project.ownerId ?? "—"}</TableCell>
                  <TableCell>{project.teamName ?? "Standalone"}</TableCell>
                  <TableCell>
                    <div className="flex flex-wrap gap-2">
                      <Button type="button" size="sm" variant="outline" onClick={() => void onChangeProjectTeam(project)}>
                        Change team
                      </Button>
                      <Button
                        type="button"
                        size="sm"
                        variant="outline"
                        disabled={Boolean(project.teamId)}
                        onClick={() => void onChangeProjectOwner(project)}
                      >
                        Change owner
                      </Button>
                    </div>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
          <div className="flex flex-col gap-2 border-t pt-4 sm:flex-row sm:items-center sm:justify-between">
            <p className="text-xs text-muted-foreground">
              {projectTotal === 0
                ? "No projects match"
                : `Showing ${projectOffset + 1}–${projectOffset + projects.length} of ${projectTotal}`}
            </p>
            <div className="flex gap-2">
              <Button type="button" variant="outline" size="sm" disabled={!projectHasPrev} onClick={goPrevProjects}>
                Previous
              </Button>
              <Button type="button" variant="outline" size="sm" disabled={!projectHasNext} onClick={goNextProjects}>
                Next
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Teams</CardTitle>
          <CardDescription>
            Search by team name or description. Server-side pagination (read-only).
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex flex-wrap items-center gap-3">
            <Input
              className="max-w-md flex-1"
              placeholder="Search teams…"
              value={teamSearch}
              onChange={(e) => setTeamSearch(e.target.value)}
            />
            <label className="flex items-center gap-2 text-sm text-muted-foreground">
              <span>Page size</span>
              <select
                className="border-input bg-background h-9 rounded-md border px-2"
                value={teamPageSize}
                onChange={(e) => {
                  const v = Number(e.target.value) as (typeof PAGE_SIZE_OPTIONS)[number];
                  setTeamPageSize(v);
                  setTeamOffset(0);
                }}
              >
                {PAGE_SIZE_OPTIONS.map((n) => (
                  <option key={n} value={n}>
                    {n}
                  </option>
                ))}
              </select>
            </label>
          </div>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Name</TableHead>
                <TableHead>Owner id</TableHead>
                <TableHead>Description</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {teams.map((t) => (
                <TableRow key={t.id}>
                  <TableCell>{t.name}</TableCell>
                  <TableCell className="font-mono text-xs">{t.ownerId ?? "—"}</TableCell>
                  <TableCell className="max-w-md truncate">{t.description ?? "—"}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
          <div className="flex flex-col gap-2 border-t pt-4 sm:flex-row sm:items-center sm:justify-between">
            <p className="text-xs text-muted-foreground">
              {teamTotal === 0
                ? "No teams match"
                : `Showing ${teamOffset + 1}–${teamOffset + teams.length} of ${teamTotal}`}
            </p>
            <div className="flex gap-2">
              <Button type="button" variant="outline" size="sm" disabled={!teamHasPrev} onClick={goPrevTeams}>
                Previous
              </Button>
              <Button type="button" variant="outline" size="sm" disabled={!teamHasNext} onClick={goNextTeams}>
                Next
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
