import { useCallback, useState } from "react";
import type { ChartDomain, SyncMode } from "@/domain/scalars/types";

export interface UseMetricDomainsResult {
  metricDomains: Record<string, ChartDomain>;
  handleDomainChange: (metricName: string, domain: ChartDomain | null) => void;
  resetDomain: (metricName: string) => void;
  resetAllDomains: () => void;
}

export function useMetricDomains(
  visibleMetricNames: string[],
  syncMode: SyncMode
): UseMetricDomainsResult {
  const [metricDomains, setMetricDomains] = useState<Record<string, ChartDomain>>({});

  const handleDomainChange = useCallback(
    (metricName: string, domain: ChartDomain | null) => {
      setMetricDomains((prev) => {
        const nextDomain = domain ?? { x: null, y: null };
        if (syncMode === "independent") {
          return { ...prev, [metricName]: nextDomain };
        }
        const next: Record<string, ChartDomain> = { ...prev };
        visibleMetricNames.forEach((name) => {
          const current = next[name] ?? { x: null, y: null };
          if (syncMode === "x-only") {
            next[name] = { x: nextDomain.x, y: current.y };
          } else if (syncMode === "y-only") {
            next[name] = { x: current.x, y: nextDomain.y };
          } else {
            next[name] = { x: nextDomain.x, y: nextDomain.y };
          }
        });
        return next;
      });
    },
    [syncMode, visibleMetricNames]
  );

  const resetDomain = useCallback(
    (metricName: string) => {
      handleDomainChange(metricName, { x: null, y: null });
    },
    [handleDomainChange]
  );

  const resetAllDomains = useCallback(() => {
    setMetricDomains(() => {
      const next: Record<string, ChartDomain> = {};
      visibleMetricNames.forEach((metricName) => {
        next[metricName] = { x: null, y: null };
      });
      return next;
    });
  }, [visibleMetricNames]);

  return {
    metricDomains,
    handleDomainChange,
    resetDomain,
    resetAllDomains,
  };
}
