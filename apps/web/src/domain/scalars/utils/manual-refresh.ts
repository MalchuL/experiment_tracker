import type { IncrementalArtifactsRefreshResult } from "@/domain/logged-objects/hooks/use-artifacts-live-refresh";
import type { IncrementalScalarsRefreshResult } from "@/domain/scalars/hooks/use-scalars-live-refresh";

export interface ManualRefreshPlan {
  refetchScalars: boolean;
  refetchArtifacts: boolean;
}

export function planManualRefreshActions(
  scalarsResult: IncrementalScalarsRefreshResult,
  artifactsResult: IncrementalArtifactsRefreshResult
): ManualRefreshPlan {
  return {
    refetchScalars: scalarsResult === "unavailable",
    refetchArtifacts: artifactsResult === "unavailable",
  };
}
