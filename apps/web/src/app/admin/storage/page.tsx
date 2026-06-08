"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { API_ROUTES } from "@/lib/constants/api-routes";
import { getPublicApiBaseUrl } from "@/lib/runtime-config";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";

const STORAGE_KEY = "experiment_tracker_admin_panel_key";

const PAGE_SIZE_OPTIONS = [25, 50, 100] as const;

type BucketRow = {
  id: string | null;
  projectId: string | null;
  experimentId: string | null;
  name: string;
  size: number;
  storageSize?: number | null;
  objectCount: number;
  registered?: boolean;
  createdAt?: string | null;
};

type ScalarTableRow = {
  name: string;
  rows: number;
  bytes: number;
};

function adminBaseUrl() {
  return getPublicApiBaseUrl();
}

async function adminFetch(pathWithQuery: string, init?: RequestInit) {
  const key = typeof window !== "undefined" ? sessionStorage.getItem(STORAGE_KEY) : null;
  const headers = new Headers(init?.headers);
  if (key) headers.set("X-Admin-Key", key);
  if (!headers.has("Content-Type") && init?.body) {
    headers.set("Content-Type", "application/json");
  }
  return fetch(`${adminBaseUrl()}/${pathWithQuery.replace(/^\//, "")}`, {
    ...init,
    headers,
  });
}

function formatBytes(bytes: number): string {
  if (!Number.isFinite(bytes) || bytes <= 0) return "0 B";
  const units = ["B", "KB", "MB", "GB", "TB"];
  let value = bytes;
  let unit = 0;
  while (value >= 1024 && unit < units.length - 1) {
    value /= 1024;
    unit += 1;
  }
  return `${value.toFixed(value >= 10 || unit === 0 ? 0 : 1)} ${units[unit]}`;
}

export default function StorageManagementPage() {
  const [buckets, setBuckets] = useState<BucketRow[]>([]);
  const [bucketTotal, setBucketTotal] = useState(0);
  const [bucketOffset, setBucketOffset] = useState(0);
  const [bucketPageSize, setBucketPageSize] = useState<(typeof PAGE_SIZE_OPTIONS)[number]>(50);

  const [scalarTables, setScalarTables] = useState<ScalarTableRow[]>([]);
  const [scalarTotal, setScalarTotal] = useState(0);
  const [scalarOffset, setScalarOffset] = useState(0);
  const [scalarPageSize, setScalarPageSize] = useState<(typeof PAGE_SIZE_OPTIONS)[number]>(50);

  const [error, setError] = useState<string | null>(null);
  const [reconcile, setReconcile] = useState(false);
  const [projectFilter, setProjectFilter] = useState("");
  const [bucketNameSearch, setBucketNameSearch] = useState("");
  const [debouncedBucketName, setDebouncedBucketName] = useState("");
  const [scalarTableSearch, setScalarTableSearch] = useState("");
  const [debouncedScalarSearch, setDebouncedScalarSearch] = useState("");

  useEffect(() => {
    const t = setTimeout(() => setDebouncedBucketName(bucketNameSearch.trim()), 400);
    return () => clearTimeout(t);
  }, [bucketNameSearch]);

  useEffect(() => {
    const t = setTimeout(() => setDebouncedScalarSearch(scalarTableSearch.trim()), 400);
    return () => clearTimeout(t);
  }, [scalarTableSearch]);

  const loadBuckets = useCallback(async () => {
    const qs = new URLSearchParams();
    qs.set("reconcile", String(reconcile));
    qs.set("limit", String(bucketPageSize));
    qs.set("offset", String(bucketOffset));
    if (projectFilter.trim()) qs.set("project_id", projectFilter.trim());
    if (debouncedBucketName) qs.set("q", debouncedBucketName);
    const bucketResponse = await adminFetch(`${API_ROUTES.ADMIN.STORAGE_BUCKETS}?${qs.toString()}`);
    if (!bucketResponse.ok) {
      setError("Failed to load buckets.");
      return;
    }
    const bucketBody = (await bucketResponse.json()) as {
      buckets: BucketRow[];
      total?: number;
    };
    setBuckets(bucketBody.buckets ?? []);
    setBucketTotal(bucketBody.total ?? bucketBody.buckets?.length ?? 0);
    setError(null);
  }, [
    reconcile,
    projectFilter,
    debouncedBucketName,
    bucketPageSize,
    bucketOffset,
  ]);

  const loadScalars = useCallback(async () => {
    const qs = new URLSearchParams();
    qs.set("limit", String(scalarPageSize));
    qs.set("offset", String(scalarOffset));
    if (debouncedScalarSearch) qs.set("q", debouncedScalarSearch);
    const scalarResponse = await adminFetch(`${API_ROUTES.ADMIN.STORAGE_SCALARS}?${qs.toString()}`);
    if (!scalarResponse.ok) {
      setError("Failed to load scalar tables.");
      return;
    }
    const scalarBody = (await scalarResponse.json()) as {
      tables: ScalarTableRow[];
      total?: number;
    };
    setScalarTables(scalarBody.tables ?? []);
    setScalarTotal(scalarBody.total ?? scalarBody.tables?.length ?? 0);
    setError(null);
  }, [scalarPageSize, scalarOffset, debouncedScalarSearch]);

  const refreshAll = useCallback(() => {
    void loadBuckets();
    void loadScalars();
  }, [loadBuckets, loadScalars]);

  useEffect(() => {
    void loadBuckets();
  }, [loadBuckets]);

  useEffect(() => {
    void loadScalars();
  }, [loadScalars]);

  const clearBucket = async (bucket: BucketRow) => {
    const isRegistered = bucket.registered ?? bucket.id != null;
    if (isRegistered && bucket.id) {
      if (
        !window.confirm(
          "Clear all objects in this bucket and remove matching metadata in the object-storage database (project CAS blobs and snapshots, or experiment artifact rows)? Scalar / ClickHouse tables are not changed.",
        )
      )
        return;
      const response = await adminFetch(API_ROUTES.ADMIN.STORAGE_BUCKET_CLEAR(bucket.id), {
        method: "POST",
      });
      if (!response.ok) {
        setError(await response.text());
        return;
      }
    } else {
      if (
        !window.confirm(
          `Clear all objects in “${bucket.name}” (orphan bucket: object storage only; empty bucket kept)? Does not touch scalars.`,
        )
      )
        return;
      const qs = new URLSearchParams({ name: bucket.name });
      const response = await adminFetch(`${API_ROUTES.ADMIN.STORAGE_BUCKET_STORAGE_ONLY_CLEAR}?${qs}`, {
        method: "POST",
      });
      if (!response.ok) {
        setError(await response.text());
        return;
      }
    }
    void loadBuckets();
  };

  const deleteBucket = async (bucket: BucketRow) => {
    const isRegistered = bucket.registered ?? bucket.id != null;
    if (isRegistered && bucket.id) {
      if (!window.confirm("Delete this bucket from the registry and remove its objects in storage?"))
        return;
      const response = await adminFetch(API_ROUTES.ADMIN.STORAGE_BUCKET(bucket.id), {
        method: "DELETE",
      });
      if (!response.ok) {
        setError(await response.text());
        return;
      }
    } else {
      if (
        !window.confirm(
          `Remove bucket “${bucket.name}” from object storage only (no registry row)? This cannot be undone.`,
        )
      )
        return;
      const qs = new URLSearchParams({ name: bucket.name });
      const response = await adminFetch(`${API_ROUTES.ADMIN.STORAGE_BUCKET_STORAGE_ONLY}?${qs}`, {
        method: "DELETE",
      });
      if (!response.ok) {
        setError(await response.text());
        return;
      }
    }
    void loadBuckets();
  };

  const reconcileBucket = async (bucket: BucketRow) => {
    if (!bucket.id) return;
    const response = await adminFetch(API_ROUTES.ADMIN.STORAGE_BUCKET_RECONCILE(bucket.id), {
      method: "POST",
    });
    if (!response.ok) {
      setError(await response.text());
      return;
    }
    void loadBuckets();
  };

  const dropScalarTable = async (tableName: string) => {
    if (!window.confirm(`Drop scalar table ${tableName}?`)) return;
    const response = await adminFetch(API_ROUTES.ADMIN.STORAGE_SCALAR_TABLE(tableName), {
      method: "DELETE",
    });
    if (!response.ok) {
      setError(await response.text());
      return;
    }
    void loadScalars();
  };

  const bucketHasPrev = bucketOffset > 0;
  const bucketHasNext = bucketOffset + buckets.length < bucketTotal;
  const scalarHasPrev = scalarOffset > 0;
  const scalarHasNext = scalarOffset + scalarTables.length < scalarTotal;

  return (
    <div className="mx-auto max-w-6xl space-y-6 p-6">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Storage Management</h1>
          <p className="text-sm text-muted-foreground">
            Debug buckets and scalar tables. Operations can be slow and destructive.
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <Button variant="outline" onClick={() => void refreshAll()}>
            Refresh all
          </Button>
          <Button asChild variant="outline">
            <Link href="/admin">Back to admin</Link>
          </Button>
        </div>
      </div>

      {error ? <p className="text-sm text-destructive">{error}</p> : null}

      <Card>
        <CardHeader>
          <CardTitle>Buckets</CardTitle>
          <CardDescription>
            Buckets listed from object storage, matched to registry rows by name when present.
            Unregistered buckets show name, tracked size (no DB row), object count, and optional
            reconciled storage. Clear removes blobs and object-storage Postgres metadata for that
            scope only (scalars / ClickHouse are untouched). Filter by project UUID and/or name
            substring; pagination is server-side.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex flex-wrap gap-2">
            <Input
              className="max-w-sm"
              placeholder="Filter by project UUID"
              value={projectFilter}
              onChange={(event) => {
                setProjectFilter(event.target.value);
                setBucketOffset(0);
              }}
            />
            <Input
              className="max-w-sm"
              placeholder="Search bucket name…"
              value={bucketNameSearch}
              onChange={(event) => {
                setBucketNameSearch(event.target.value);
                setBucketOffset(0);
              }}
            />
            <Button variant="outline" onClick={() => setReconcile((value) => !value)}>
              {reconcile ? "Disable reconciliation" : "Enable reconciliation"}
            </Button>
            <label className="flex items-center gap-2 text-sm text-muted-foreground">
              <span>Page size</span>
              <select
                className="border-input bg-background h-9 rounded-md border px-2"
                value={bucketPageSize}
                onChange={(e) => {
                  setBucketPageSize(Number(e.target.value) as (typeof PAGE_SIZE_OPTIONS)[number]);
                  setBucketOffset(0);
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
                <TableHead>Project</TableHead>
                <TableHead>Experiment</TableHead>
                <TableHead>Tracked size</TableHead>
                <TableHead>Objects</TableHead>
                <TableHead />
              </TableRow>
            </TableHeader>
            <TableBody>
              {buckets.map((bucket) => {
                const registered = bucket.registered ?? bucket.id != null;
                return (
                <TableRow key={bucket.name}>
                  <TableCell className="font-mono text-xs">{bucket.name}</TableCell>
                  <TableCell className="font-mono text-xs">
                    {registered && bucket.projectId ? bucket.projectId : "—"}
                  </TableCell>
                  <TableCell className="font-mono text-xs">
                    {registered
                      ? bucket.experimentId ?? "project"
                      : "—"}
                  </TableCell>
                  <TableCell>
                    <span>{formatBytes(bucket.size)}</span>
                    {reconcile && bucket.storageSize != null ? (
                      <span className="text-muted-foreground block text-xs">
                        {formatBytes(bucket.storageSize)} in storage (reconciled)
                      </span>
                    ) : null}
                  </TableCell>
                  <TableCell>{bucket.objectCount}</TableCell>
                  <TableCell className="flex flex-wrap items-center justify-end gap-1 sm:space-x-0">
                    <Button size="sm" variant="secondary" onClick={() => void clearBucket(bucket)}>
                      Clear
                    </Button>
                    <Button
                      size="sm"
                      variant="outline"
                      disabled={!registered || !bucket.id}
                      onClick={() => void reconcileBucket(bucket)}
                    >
                      Reconcile
                    </Button>
                    <Button size="sm" variant="destructive" onClick={() => void deleteBucket(bucket)}>
                      Remove
                    </Button>
                  </TableCell>
                </TableRow>
                );
              })}
            </TableBody>
          </Table>
          <div className="flex flex-col gap-2 border-t pt-4 sm:flex-row sm:items-center sm:justify-between">
            <p className="text-xs text-muted-foreground">
              {bucketTotal === 0
                ? "No buckets in this view"
                : `Buckets ${bucketOffset + 1}–${bucketOffset + buckets.length} of ${bucketTotal}`}
            </p>
            <div className="flex gap-2">
              <Button
                type="button"
                variant="outline"
                size="sm"
                disabled={!bucketHasPrev}
                onClick={() => setBucketOffset((o) => Math.max(0, o - bucketPageSize))}
              >
                Previous
              </Button>
              <Button
                type="button"
                variant="outline"
                size="sm"
                disabled={!bucketHasNext}
                onClick={() => setBucketOffset((o) => o + bucketPageSize)}
              >
                Next
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Scalars</CardTitle>
          <CardDescription>
            ClickHouse scalar, artifacts_info, and last_logged-style tables. Search filters table names
            (alphanumeric fragment); pagination is server-side.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex flex-wrap items-center gap-3">
            <Input
              className="max-w-md"
              placeholder="Search table name (e.g. project uuid fragment)…"
              value={scalarTableSearch}
              onChange={(e) => {
                setScalarTableSearch(e.target.value);
                setScalarOffset(0);
              }}
            />
            <label className="flex items-center gap-2 text-sm text-muted-foreground">
              <span>Page size</span>
              <select
                className="border-input bg-background h-9 rounded-md border px-2"
                value={scalarPageSize}
                onChange={(e) => {
                  setScalarPageSize(Number(e.target.value) as (typeof PAGE_SIZE_OPTIONS)[number]);
                  setScalarOffset(0);
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
                <TableHead>Table</TableHead>
                <TableHead>Rows</TableHead>
                <TableHead>Bytes</TableHead>
                <TableHead />
              </TableRow>
            </TableHeader>
            <TableBody>
              {scalarTables.map((table) => (
                <TableRow key={table.name}>
                  <TableCell className="font-mono text-xs">{table.name}</TableCell>
                  <TableCell>{table.rows}</TableCell>
                  <TableCell>{formatBytes(table.bytes)}</TableCell>
                  <TableCell className="text-right">
                    <Button size="sm" variant="destructive" onClick={() => void dropScalarTable(table.name)}>
                      Drop
                    </Button>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
          <div className="flex flex-col gap-2 border-t pt-4 sm:flex-row sm:items-center sm:justify-between">
            <p className="text-xs text-muted-foreground">
              {scalarTotal === 0
                ? "No scalar tables in this view"
                : `Tables ${scalarOffset + 1}–${scalarOffset + scalarTables.length} of ${scalarTotal}`}
            </p>
            <div className="flex gap-2">
              <Button
                type="button"
                variant="outline"
                size="sm"
                disabled={!scalarHasPrev}
                onClick={() => setScalarOffset((o) => Math.max(0, o - scalarPageSize))}
              >
                Previous
              </Button>
              <Button
                type="button"
                variant="outline"
                size="sm"
                disabled={!scalarHasNext}
                onClick={() => setScalarOffset((o) => o + scalarPageSize)}
              >
                Next
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
