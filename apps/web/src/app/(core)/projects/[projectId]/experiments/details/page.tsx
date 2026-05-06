import { Suspense } from "react";
import { ExperimentDetailsView } from "@/domain/experiments/components/experiment-details-view";

export default async function ExperimentDetailsPage({
  params,
}: {
  params: Promise<{ projectId: string }>;
}) {
  const { projectId } = await params;
  return (
    <Suspense fallback={<div className="p-6 text-sm text-muted-foreground">Loading…</div>}>
      <ExperimentDetailsView projectId={projectId} />
    </Suspense>
  );
}
