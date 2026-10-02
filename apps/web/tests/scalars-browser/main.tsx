import { useCallback, useEffect, useMemo, useState } from "react";
import { createRoot } from "react-dom/client";
import {
  QueryClient,
  QueryClientProvider,
  useQuery,
} from "@tanstack/react-query";
import { ScalarsContentPanel } from "@/domain/scalars/components/scalars-content-panel";
import { ScalarChartCard } from "@/domain/scalars/components/charts/scalar-chart-card";
import { MetricChart } from "@/domain/scalars/components/metric-chart";
import { useScalarsLiveRefresh } from "@/domain/scalars/hooks/use-scalars-live-refresh";
import { scalarsService } from "@/domain/scalars/services/scalars-service";
import { buildChartDataByMetric } from "@/domain/scalars/utils/scalars-data-model";
import type { Experiment } from "@/domain/experiments/types";
import type {
  ChartDomain,
  ExperimentScalarsPoints,
} from "@/domain/scalars/types";
import "../../src/app/globals.css";

const baseline = new URLSearchParams(location.search).has("baseline");
const noop = () => {};
const client = new QueryClient({
  defaultOptions: { queries: { retry: false } },
});
const catalog: { names: string[]; experiments: Experiment[] } = await fetch(
  "/catalog.json",
).then((response) => response.json());
const experimentIds = catalog.experiments.map((experiment) => experiment.id);
declare global {
  interface Window {
    scalarBench: { preparationMs: number; steps: Record<string, number[]> };
  }
}

function Charts({
  scalars,
  activeNames,
  onVisibility,
  refresh,
}: {
  scalars: ExperimentScalarsPoints[];
  activeNames: string[];
  onVisibility?: (name: string, visible: boolean) => void;
  refresh?: () => Promise<unknown>;
}) {
  const [page, setPage] = useState(1);
  const [size, setSize] = useState(12);
  const [fullscreen, setFullscreen] = useState<string | null>(null);
  const [domains, setDomains] = useState<Record<string, ChartDomain>>({});
  const { data, preparationMs } = useMemo(() => {
    // Profiling the actual preparation work is intentional in this benchmark only.
    // eslint-disable-next-line react-hooks/purity
    const started = performance.now();
    const data = buildChartDataByMetric({
      scalars,
      allLoggedMetricNames: activeNames,
      visibleExperiments: catalog.experiments,
      smoothing: 0,
    });
    // eslint-disable-next-line react-hooks/purity
    return { data, preparationMs: performance.now() - started };
  }, [scalars, activeNames]);
  useEffect(() => {
    window.scalarBench = {
      preparationMs,
      steps: Object.fromEntries(
        Object.entries(data).map(([name, points]) => [
          name,
          points.map((point) => point.step),
        ]),
      ),
    };
  }, [data, preparationMs]);
  const domainChange = (name: string, domain: ChartDomain | null) =>
    setDomains((previous) => ({
      ...previous,
      [name]: domain ?? { x: null, y: null },
    }));
  const resetDomain = (name: string) => domainChange(name, null);
  const shared = {
    experiments: {
      allExperiments: catalog.experiments,
      visibleExperiments: catalog.experiments,
    },
    size: { cardHeight: 300, cardMinWidth: 560, onResizeCards: noop },
    zoom: {
      metricDomains: domains,
      onResetDomain: resetDomain,
      onDomainChange: domainChange,
    },
    actions: {
      onExpandMetric: setFullscreen,
      onHideMetric: noop,
      onHoverModeChange: noop,
      onPointContextMenu: noop,
    },
  };
  return (
    <>
      <button onClick={() => void refresh?.()}>Refresh</button>
      {fullscreen && (
        <div
          role="dialog"
          style={{
            position: "fixed",
            inset: 30,
            zIndex: 100,
            background: "white",
          }}
        >
          <button onClick={() => setFullscreen(null)}>Close fullscreen</button>
          <MetricChart
            metricName={fullscreen}
            data={data[fullscreen] ?? []}
            experiments={{
              selectedExperiments: catalog.experiments,
              allExperiments: catalog.experiments,
            }}
            viewport={{
              height: 600,
            }}
            zoom={{
              domain: domains[fullscreen],
              onDomainChange: (domain) => domainChange(fullscreen, domain),
            }}
          />
        </div>
      )}
      <div data-scalar-scroll-root style={{ height: 680, overflow: "auto" }}>
        {baseline ? (
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "repeat(2, 560px)",
              gap: 12,
            }}
          >
            {catalog.names.map((name) => (
              <ScalarChartCard
                key={name}
                {...shared}
                metricName={name}
                data={data[name] ?? []}
                zoom={{
                  ...shared.zoom,
                  domain: domains[name] ?? { x: null, y: null },
                }}
                display={{
                  smoothing: 0,
                  dotThreshold: 10,
                  hoverMode: "compare",
                  hoverNameMaxLength: 50,
                }}
              />
            ))}
          </div>
        ) : (
          <ScalarsContentPanel
            scalars={{
              ...shared,
              loading: {
                onMetricVisibilityChange: onVisibility!,
                statusByMetric: {},
              },
              metrics: {
                visibleMetrics: catalog.names.map((name) => ({ name })),
                chartDataByMetric: data,
              },
            }}
            pagination={{
              scalarPage: page,
              scalarPageSize: size,
              onPageChange: setPage,
              onPageSizeChange: (size) => {
                setSize(size);
                setPage(1);
              },
            }}
            artifacts={{
              data: {
                projectId: "benchmark",
                objectGroups: {},
                hiddenArtifactIds: new Set(),
                onImagePreview: noop,
              },
              steps: {
                objectStepSelection: {},
                updateObjectStep: noop,
                debouncedObjectStepSelection: {},
              },
              overrides: {
                experimentStepOverrideEnabled: {},
                setExperimentStepOverrideEnabled: noop,
                enableExperimentStepOverride: noop,
                experimentStepOverrides: {},
                updateExperimentStepOverride: noop,
                debouncedExperimentStepOverrides: {},
              },
            }}
          />
        )}
      </div>
    </>
  );
}
function Baseline() {
  const { data } = useQuery({
    queryKey: ["baseline"],
    queryFn: () =>
      scalarsService.getAllByProject("benchmark", {
        experimentIds,
        maxPoints: 1000,
      }),
  });
  return <Charts scalars={data?.data ?? []} activeNames={catalog.names} />;
}
function Improved() {
  const [mounted, setMounted] = useState<string[]>([]);
  const visibility = useCallback(
    (name: string, visible: boolean) =>
      setMounted((previous) =>
        previous.includes(name) === visible
          ? previous
          : visible
            ? [...previous, name]
            : previous.filter((item) => item !== name),
      ),
    [],
  );
  const result = useScalarsLiveRefresh({
    projectId: "benchmark",
    experimentIds,
    scalarNames: mounted,
    maxPoints: 1000,
    enabled: false,
  });
  return (
    <Charts
      scalars={result.scalars}
      activeNames={mounted}
      onVisibility={visibility}
      refresh={result.refreshChangedScalars}
    />
  );
}
createRoot(document.getElementById("root")!).render(
  <QueryClientProvider client={client}>
    {baseline ? <Baseline /> : <Improved />}
  </QueryClientProvider>,
);
