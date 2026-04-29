"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { env } from "@/lib/env";
import { API_ROUTES } from "@/lib/constants/api-routes";
import { Button } from "@/components/ui/button";
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

const STORAGE_KEY = "experiment_tracker_admin_panel_key";

const PAGE_SIZE = 20;

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
  ownerId: string;
  createdAt: string | null;
};

function adminBaseUrl() {
  return env.BASE_URL.replace(/\/$/, "");
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

async function probeAdminKey(adminKey: string): Promise<boolean> {
  const r = await adminFetch(
    `${API_ROUTES.ADMIN.USERS}?limit=1&offset=0`,
    undefined,
    { adminKey },
  );
  return r.ok;
}

export default function AdminPage() {
  const [keyInput, setKeyInput] = useState("");
  const [unlocked, setUnlocked] = useState(false);
  const [search, setSearch] = useState("");
  const [teamSearch, setTeamSearch] = useState("");
  const [userOffset, setUserOffset] = useState(0);
  const [teamOffset, setTeamOffset] = useState(0);
  const [users, setUsers] = useState<AdminUserRow[]>([]);
  const [teams, setTeams] = useState<AdminTeamRow[]>([]);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [resetResult, setResetResult] = useState<{ email: string; password: string } | null>(null);
  const [unlockError, setUnlockError] = useState<string | null>(null);
  const [unlocking, setUnlocking] = useState(false);

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
    setUserOffset(0);
    setTeamOffset(0);
    setResetResult(null);
    setLoadError(null);
    setUnlockError(message);
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
    setUserOffset(0);
    setTeamOffset(0);
    setResetResult(null);
    setUnlockError(null);
    setLoadError(null);
  };

  const loadTeams = useCallback(
    async (q: string, offset: number) => {
      const qs = new URLSearchParams();
      qs.set("limit", String(PAGE_SIZE));
      qs.set("offset", String(offset));
      if (q.trim()) qs.set("q", q.trim());
      const r = await adminFetch(`${API_ROUTES.ADMIN.TEAMS}?${qs.toString()}`);
      if (r.status === 403) {
        invalidateAdminSession("Admin key was rejected. Unlock again.");
        return;
      }
      if (!r.ok) {
        setLoadError(await r.text());
        return;
      }
      setLoadError(null);
      setTeams(await r.json());
    },
    [invalidateAdminSession],
  );

  const loadUsers = useCallback(
    async (q: string, offset: number) => {
      const qs = new URLSearchParams();
      qs.set("limit", String(PAGE_SIZE));
      qs.set("offset", String(offset));
      if (q.trim()) qs.set("q", q.trim());
      const r = await adminFetch(`${API_ROUTES.ADMIN.USERS}?${qs.toString()}`);
      if (r.status === 403) {
        invalidateAdminSession("Admin key was rejected. Unlock again.");
        return;
      }
      if (!r.ok) {
        setLoadError(await r.text());
        return;
      }
      setLoadError(null);
      setUsers(await r.json());
    },
    [invalidateAdminSession],
  );

  useEffect(() => {
    if (!unlocked) return;
    const t = setTimeout(() => {
      setUserOffset(0);
      void loadUsers(search, 0);
    }, 300);
    return () => clearTimeout(t);
  }, [unlocked, search, loadUsers]);

  useEffect(() => {
    if (!unlocked) return;
    const t = setTimeout(() => {
      setTeamOffset(0);
      void loadTeams(teamSearch, 0);
    }, 300);
    return () => clearTimeout(t);
  }, [unlocked, teamSearch, loadTeams]);

  const userHasPrev = userOffset > 0;
  const userHasNext = users.length >= PAGE_SIZE;

  const teamHasPrev = teamOffset > 0;
  const teamHasNext = teams.length >= PAGE_SIZE;

  const goPrevUsers = () => {
    const nextOffset = Math.max(0, userOffset - PAGE_SIZE);
    setUserOffset(nextOffset);
    void loadUsers(search, nextOffset);
  };

  const goNextUsers = () => {
    const nextOffset = userOffset + PAGE_SIZE;
    setUserOffset(nextOffset);
    void loadUsers(search, nextOffset);
  };

  const goPrevTeams = () => {
    const nextOffset = Math.max(0, teamOffset - PAGE_SIZE);
    setTeamOffset(nextOffset);
    void loadTeams(teamSearch, nextOffset);
  };

  const goNextTeams = () => {
    const nextOffset = teamOffset + PAGE_SIZE;
    setTeamOffset(nextOffset);
    void loadTeams(teamSearch, nextOffset);
  };

  const onReset = async (userId: string, email: string) => {
    setResetResult(null);
    const r = await adminFetch(API_ROUTES.ADMIN.RESET_PASSWORD(userId), { method: "POST" });
    if (r.status === 403) {
      invalidateAdminSession("Admin key was rejected. Unlock again.");
      return;
    }
    if (!r.ok) {
      setLoadError(await r.text());
      return;
    }
    const body = (await r.json()) as { temporaryPassword: string };
    setResetResult({ email, password: body.temporaryPassword });
    void loadUsers(search, userOffset);
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
    <div className="mx-auto max-w-5xl space-y-8 p-6">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h1 className="text-2xl font-semibold tracking-tight">Admin</h1>
        <Button variant="outline" onClick={lock}>
          Lock / clear key
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
            Search by email or display name. Loads {PAGE_SIZE} rows per request.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <Input
            placeholder="Search…"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Email</TableHead>
                <TableHead>Display name</TableHead>
                <TableHead>Active</TableHead>
                <TableHead className="w-[120px]" />
              </TableRow>
            </TableHeader>
            <TableBody>
              {users.map((u) => (
                <TableRow key={u.id}>
                  <TableCell>{u.email}</TableCell>
                  <TableCell>{u.displayName ?? "—"}</TableCell>
                  <TableCell>{u.isActive ? "yes" : "no"}</TableCell>
                  <TableCell>
                    <Button
                      type="button"
                      variant="secondary"
                      size="sm"
                      onClick={() => void onReset(u.id, u.email)}
                    >
                      Reset password
                    </Button>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
          <div className="flex flex-col gap-2 border-t pt-4 sm:flex-row sm:items-center sm:justify-between">
            <p className="text-xs text-muted-foreground">
              Offset {userOffset}
              {users.length > 0 ? ` · ${users.length} row${users.length === 1 ? "" : "s"} on this page` : ""}
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
          <CardTitle>Teams</CardTitle>
          <CardDescription>
            Search by team name or description. Loads {PAGE_SIZE} rows per request (read-only).
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <Input
            placeholder="Search teams…"
            value={teamSearch}
            onChange={(e) => setTeamSearch(e.target.value)}
          />
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
                  <TableCell className="font-mono text-xs">{t.ownerId}</TableCell>
                  <TableCell className="max-w-md truncate">{t.description ?? "—"}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
          <div className="flex flex-col gap-2 border-t pt-4 sm:flex-row sm:items-center sm:justify-between">
            <p className="text-xs text-muted-foreground">
              Offset {teamOffset}
              {teams.length > 0 ? ` · ${teams.length} row${teams.length === 1 ? "" : "s"} on this page` : ""}
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