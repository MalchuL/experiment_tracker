"use client";

import { useEffect, useState } from "react";
import { PageHeader } from "@/components/shared/page-header";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { API_ROUTES } from "@/lib/constants/api-routes";
import {
  WEB_APP_DESCRIPTION,
  WEB_APP_NAME,
  WEB_APP_VERSION,
  type AboutInfo,
} from "@/lib/constants/app-info";
import { getPublicApiBaseUrl } from "@/lib/runtime-config";

function InfoRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="grid gap-1 sm:grid-cols-[9rem_minmax(0,1fr)] sm:items-start sm:gap-4">
      <dt className="text-sm font-medium text-muted-foreground">{label}</dt>
      <dd className="text-sm break-all">{value}</dd>
    </div>
  );
}

export default function AboutPage() {
  const backendUrl = getPublicApiBaseUrl();
  const [backendAbout, setBackendAbout] = useState<AboutInfo | null>(null);
  const [backendError, setBackendError] = useState<string | null>(null);
  const [loadingBackend, setLoadingBackend] = useState(true);

  useEffect(() => {
    let cancelled = false;

    void (async () => {
      setLoadingBackend(true);
      setBackendError(null);
      try {
        const response = await fetch(`${backendUrl}/${API_ROUTES.ABOUT}`);
        if (!response.ok) {
          throw new Error(`${response.status} ${response.statusText}`.trim());
        }
        const body = (await response.json()) as AboutInfo;
        if (!cancelled) {
          setBackendAbout(body);
        }
      } catch (error) {
        if (!cancelled) {
          setBackendAbout(null);
          setBackendError(error instanceof Error ? error.message : "Failed to load backend info");
        }
      } finally {
        if (!cancelled) {
          setLoadingBackend(false);
        }
      }
    })();

    return () => {
      cancelled = true;
    };
  }, [backendUrl]);

  return (
    <div className="mx-auto flex w-full max-w-3xl flex-col gap-6 p-6">
      <PageHeader
        title="About"
        description="Build and deployment details for this Experiment Tracker instance."
      />

      <Card>
        <CardHeader>
          <CardTitle>{WEB_APP_NAME}</CardTitle>
          <CardDescription>{WEB_APP_DESCRIPTION}</CardDescription>
        </CardHeader>
        <CardContent>
          <dl className="space-y-4">
            <InfoRow label="Web UI version" value={WEB_APP_VERSION} />
          </dl>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Backend API</CardTitle>
          <CardDescription>Main API used by the web app and SDK.</CardDescription>
        </CardHeader>
        <CardContent>
          <dl className="space-y-4">
            <InfoRow label="Backend URL" value={backendUrl} />
            {loadingBackend ? (
              <InfoRow label="Backend version" value="Loading…" />
            ) : backendAbout ? (
              <>
                <InfoRow label="Service" value={backendAbout.service} />
                <InfoRow label="Backend version" value={backendAbout.version} />
                <InfoRow label="Description" value={backendAbout.description} />
              </>
            ) : (
              <InfoRow
                label="Backend version"
                value={backendError ?? "Unable to load backend metadata"}
              />
            )}
          </dl>
        </CardContent>
      </Card>
    </div>
  );
}
