// @vitest-environment jsdom
import {
  act,
  createElement as h,
  useCallback,
  useEffect,
  useState,
} from "react";
import { createRoot, type Root } from "react-dom/client";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { useScalarsLiveRefresh } from "./hooks/use-scalars-live-refresh";
import { ScalarsContentPanel } from "./components/scalars-content-panel";
import { CreateMetricFromPointDialog } from "./components/metric-create/create-metric-from-point-dialog";
import { useScalarsQueryState } from "./hooks/use-scalars-query-state";
import type { Experiment } from "@/domain/experiments/types";
import type { ReadonlyURLSearchParams } from "next/navigation";

const http = vi.hoisted(() => ({ get: vi.fn(), post: vi.fn() }));
vi.mock("@/lib/api/clients/axios-client", () => ({
  serviceClients: { api: http },
}));
vi.mock("./components/metric-chart", () => ({
  MetricChart: () => h("div", { "data-plot": true }),
}));
vi.mock("./components/logged-objects-section", () => ({
  LoggedObjectsSection: () => null,
}));

const timestamp = (step: number) =>
  new Date(Date.UTC(2026, 0, 1, 0, 0, step)).toISOString();
const experiment = {
  id: "exp",
  name: "Experiment",
  createdAt: timestamp(0),
  status: "complete",
} as Experiment;
const experiments = [experiment];
const names = Array.from(
  { length: 36 },
  (_, index) => `loss${String(index).padStart(2, "0")}`,
);
const pageResult = <T>(data: T[], hasNext = false) => ({
  data,
  size: data.length,
  total: data.length,
  hasNext,
});
let step: number;
let root: Root;
let host: HTMLDivElement;
let client: QueryClient;
let latest: ReturnType<typeof useScalarsLiveRefresh>;

class Observer {
  static instances: Observer[] = [];
  elements = new Set<Element>();
  constructor(
    public callback: IntersectionObserverCallback,
    public options: IntersectionObserverInit,
  ) {
    Observer.instances.push(this);
  }
  observe = (element: Element) => this.elements.add(element);
  unobserve = (element: Element) => this.elements.delete(element);
  disconnect = () => this.elements.clear();
}
async function settle() {
  await act(async () => {
    await new Promise((resolve) => setTimeout(resolve, 25));
  });
}
async function render(child: React.ReactNode) {
  await act(async () => root.render(h(QueryClientProvider, { client }, child)));
  await settle();
}
async function show(name: string, visible = true) {
  const target = host.querySelector(`[data-scalar-placeholder="${name}"]`)!;
  expect(target).not.toBeNull();
  await act(async () => {
    for (const observer of Observer.instances)
      if (observer.elements.has(target)) {
        observer.callback(
          [{ target, isIntersecting: visible } as IntersectionObserverEntry],
          observer as unknown as IntersectionObserver,
        );
      }
  });
  await settle();
}
function Hook({
  names = ["loss00"],
  ids = ["exp"],
  auto = false,
}: {
  names?: string[];
  ids?: string[];
  auto?: boolean;
}) {
  const result = useScalarsLiveRefresh({
    projectId: "project",
    experimentIds: ids,
    scalarNames: names,
    maxPoints: 100,
    enabled: auto,
  });
  useEffect(() => {
    latest = result;
  }, [result]);
  return null;
}
function Grid({ grouped = false }: { grouped?: boolean }) {
  const [mounted, setMounted] = useState<string[]>([]);
  const [page, setPage] = useState(1);
  const [size, setSize] = useState(12);
  const visibility = useCallback(
    (name: string, visible: boolean) =>
      setMounted((previous) => {
        if (previous.includes(name) === visible) return previous;
        return visible
          ? [...previous, name]
          : previous.filter((item) => item !== name);
      }),
    [],
  );
  const result = useScalarsLiveRefresh({
    projectId: "project",
    experimentIds: ["exp"],
    scalarNames: mounted,
    maxPoints: 100,
    enabled: false,
  });
  useEffect(() => {
    latest = result;
  }, [result]);
  const data = Object.fromEntries(
    result.scalars.flatMap((entry) =>
      Object.entries(entry.scalars).map(([name, series]) => [
        name,
        series.x.map((step, i) => ({
          step,
          exp: { original: series.y[i], smoothed: series.y[i] },
        })),
      ]),
    ),
  );
  return h(
    "div",
    { "data-scalar-scroll-root": true },
    h(ScalarsContentPanel, {
      scalars: {
        experiments: {
          allExperiments: experiments,
          visibleExperiments: experiments,
        },
        size: {
          cardHeight: 200,
          cardMinWidth: 300,
        },
        zoom: {
          metricDomains: {},
          onResetDomain: vi.fn(),
          onDomainChange: vi.fn(),
        },
        actions: {
          onExpandMetric: vi.fn(),
          onHideMetric: vi.fn(),
        },
        loading: {
          onMetricVisibilityChange: visibility,
          statusByMetric: result.statusByMetric,
        },
        metrics: {
          visibleMetrics: names.map((name) => ({
            name: grouped ? `train/${name}` : name,
          })),
          chartDataByMetric: data,
        },
      },
      pagination: {
        scalarPage: page,
        scalarPageSize: size,
        onPageChange: setPage,
        onPageSizeChange: (size) => {
          setSize(size);
          setPage(1);
        },
      },
      artifacts: {
        data: {
          projectId: "project",
          objectGroups: {
            image: { preview: { steps: [1], byExperiment: {} } },
          },
          hiddenArtifactIds: new Set<string>(),
          onImagePreview: vi.fn(),
        },
        steps: {
          objectStepSelection: {},
          updateObjectStep: vi.fn(),
          debouncedObjectStepSelection: {},
        },
        overrides: {
          experimentStepOverrideEnabled: {},
          setExperimentStepOverrideEnabled: vi.fn(),
          enableExperimentStepOverride: vi.fn(),
          experimentStepOverrides: {},
          updateExperimentStepOverride: vi.fn(),
          debouncedExperimentStepOverrides: {},
        },
      },
    }),
  );
}

beforeEach(() => {
  Object.assign(globalThis, { IS_REACT_ACT_ENVIRONMENT: true });
  vi.stubGlobal("IntersectionObserver", Observer);
  Observer.instances = [];
  step = 1;
  client = new QueryClient({
    defaultOptions: { queries: { retry: false, gcTime: 600_000 } },
  });
  host = document.createElement("div");
  document.body.append(host);
  root = createRoot(host);
  http.post.mockImplementation(async () => ({
    data: pageResult([
      { experiment_id: "exp", last_modified: timestamp(step) },
    ]),
  }));
  http.get.mockImplementation(async (url: string) => {
    const params = new URL(url, "http://localhost").searchParams;
    const start = params.get("start_time");
    const from = start
      ? (Date.parse(start) - Date.parse(timestamp(0))) / 1000
      : 0;
    const x = Array.from(
      { length: step - from + 1 },
      (_, index) => index + from,
    );
    return {
      data: pageResult([
        {
          experiment_id: "exp",
          scalars: { [params.get("scalar_name")!]: { x, y: x } },
        },
      ]),
    };
  });
});
afterEach(async () => {
  await act(async () => root.unmount());
  client.clear();
  host.remove();
  vi.clearAllMocks();
  vi.unstubAllGlobals();
  vi.useRealTimers();
});

describe("scalar lifecycle", () => {
  it("loads only visible cards, paginates, and restores sampled history on return", async () => {
    await render(h(Grid));
    expect(host.querySelectorAll("[data-scalar-placeholder]")).toHaveLength(12);
    expect(http.get).not.toHaveBeenCalled();
    await show("loss00");
    expect(http.get).toHaveBeenCalledTimes(1);
    expect(host.querySelectorAll("[data-plot]")).toHaveLength(1);
    expect(
      Observer.instances.filter((observer) => observer.elements.size).length,
    ).toBe(1);
    expect(Observer.instances[0].options.root).toBe(host.firstElementChild);
    await act(async () =>
      [...host.querySelectorAll("button")]
        .find((button) => button.textContent === "Next")!
        .click(),
    );
    await settle();
    expect(host.querySelector('[data-scalar-placeholder="loss00"]')).toBeNull();
    expect(host.querySelectorAll("[data-plot]")).toHaveLength(0);
    step = 8;
    await show("loss12");
    expect(
      new URL(
        http.get.mock.calls.at(-1)![0],
        "http://localhost",
      ).searchParams.has("start_time"),
    ).toBe(false);
    await act(async () =>
      [...host.querySelectorAll("button")]
        .find((button) => button.textContent === "Previous")!
        .click(),
    );
    await show("loss00");
    expect(
      new URL(
        http.get.mock.calls.at(-1)![0],
        "http://localhost",
      ).searchParams.get("start_time"),
    ).toBe(timestamp(1));
    expect(latest.scalars[0].scalars.loss00.x).toEqual([
      0, 1, 2, 3, 4, 5, 6, 7, 8,
    ]);
    await show("loss00", false);
    expect(host.querySelectorAll("[data-plot]")).toHaveLength(0);
  });

  it("unsubscribes collapsed groups and inactive scalar tabs", async () => {
    await render(h(Grid, { grouped: true }));
    await show("train/loss00");
    const group = [...host.querySelectorAll("button")].find((button) =>
      button.textContent?.startsWith("train "),
    )!;
    await act(async () => group.click());
    await settle();
    expect(host.querySelectorAll("[data-plot]")).toHaveLength(0);
    expect(latest.scalars).toEqual([]);
    step = 4;
    await act(async () => group.click());
    await show("train/loss00");
    expect(latest.scalars[0].scalars["train/loss00"].x.at(-1)).toBe(4);
    const imageTab = [...host.querySelectorAll('[role="tab"]')].find(
      (tab) => tab.textContent === "Image",
    )!;
    await act(async () =>
      imageTab.dispatchEvent(
        new MouseEvent("mousedown", { bubbles: true, button: 0 }),
      ),
    );
    await settle();
    expect(host.querySelectorAll("[data-scalar-placeholder]")).toHaveLength(0);
    expect(latest.scalars).toEqual([]);
  });

  it("restores after route unmount, checks completed experiments, and recovers a failed refresh", async () => {
    await render(h(Hook));
    await render(null);
    step = 5;
    http.get.mockRejectedValueOnce(new Error("network failure"));
    await render(h(Hook));
    expect(latest.statusByMetric.loss00.error).toBe(true);
    expect(latest.scalars[0].scalars.loss00.x).toEqual([0, 1]);
    await act(async () => {
      await latest.refreshChangedScalars();
    });
    await settle();
    expect(latest.scalars[0].scalars.loss00.x).toEqual([0, 1, 2, 3, 4, 5]);
    const calls = http.get.mock.calls
      .slice(-2)
      .map(([url]) =>
        new URL(url, "http://localhost").searchParams.get("start_time"),
      );
    expect(calls).toEqual([timestamp(1), timestamp(1)]);
  });

  it("does not commit half a paginated response or duplicate experiments", async () => {
    await render(h(Hook));
    step = 3;
    http.get.mockResolvedValueOnce({
      data: pageResult(
        [{ experiment_id: "exp", scalars: { loss00: { x: [2], y: [2] } } }],
        true,
      ),
    });
    http.get.mockRejectedValueOnce(new Error("page two failed"));
    await act(async () => {
      await latest.refreshChangedScalars();
    });
    await settle();
    expect(latest.scalars[0].scalars.loss00.x).toEqual([0, 1]);
    await act(async () => {
      await latest.refreshChangedScalars();
    });
    await settle();
    expect(latest.scalars).toHaveLength(1);
    expect(latest.scalars[0].scalars.loss00.x).toEqual([0, 1, 2, 3]);
  });

  it("deduplicates concurrent manual refresh and discards a response after unmount", async () => {
    await render(h(Hook));
    step = 4;
    let resolve!: (value: unknown) => void;
    http.get.mockImplementationOnce(
      () =>
        new Promise((done) => {
          resolve = done;
        }),
    );
    let first!: Promise<unknown>;
    let second!: Promise<unknown>;
    await act(async () => {
      first = latest.refreshChangedScalars();
      second = latest.refreshChangedScalars();
    });
    await settle();
    expect(http.get).toHaveBeenCalledTimes(2);
    const signal = http.get.mock.calls.at(-1)![1].signal as AbortSignal;
    await render(null);
    expect(signal.aborted).toBe(true);
    resolve({
      data: pageResult([
        { experiment_id: "exp", scalars: { loss00: { x: [999], y: [999] } } },
      ]),
    });
    await Promise.all([first, second]);
    await render(h(Hook));
    expect(latest.scalars[0].scalars.loss00.x).toEqual([0, 1, 2, 3, 4]);
  });

  it("fetches a full baseline after eviction and skips an empty experiment selection", async () => {
    await render(h(Hook));
    await render(null);
    client.clear();
    step = 9;
    await render(h(Hook));
    expect(
      new URL(
        http.get.mock.calls.at(-1)![0],
        "http://localhost",
      ).searchParams.has("start_time"),
    ).toBe(false);
    http.get.mockClear();
    await render(h(Hook, { ids: [] }));
    await act(async () => {
      await latest.refreshChangedScalars();
    });
    expect(http.get).not.toHaveBeenCalled();
    expect(latest.scalars).toEqual([]);
  });

  it("pauses timed refresh without disabling initial loading or manual catch-up", async () => {
    vi.useFakeTimers({ toFake: ["setInterval", "clearInterval"] });
    await render(h(Hook, { auto: false }));
    step = 3;
    await act(async () => {
      vi.advanceTimersByTime(60_000);
    });
    await settle();
    expect(http.get).toHaveBeenCalledTimes(1);
    await render(h(Hook, { auto: true }));
    await act(async () => {
      vi.advanceTimersByTime(30_000);
    });
    await settle();
    expect(latest.scalars[0].scalars.loss00.x.at(-1)).toBe(3);
  });

  it("preserves metric creation from the original scalar value", async () => {
    const submit = vi.fn();
    await render(
      h(CreateMetricFromPointDialog, {
        point: {
          experimentId: "exp",
          experimentName: "Experiment",
          metricName: "loss00",
          step: 10,
          originalValue: 0.125,
          smoothedValue: 0.9,
        },
        open: true,
        isSaving: false,
        onOpenChange: vi.fn(),
        onSubmit: submit,
      }),
    );
    await act(async () =>
      [...document.querySelectorAll("button")]
        .find((button) => button.textContent === "Create metric")!
        .click(),
    );
    expect(submit).toHaveBeenCalledWith({
      experimentId: "exp",
      name: "loss00",
      value: 0.125,
      label: null,
    });
  });

  it("restores pagination from saved views and resets it on filters", async () => {
    let state!: ReturnType<typeof useScalarsQueryState>;
    const params = new URLSearchParams(
      "page=3&pageSize=24",
    ) as ReadonlyURLSearchParams;
    function State() {
      const value = useScalarsQueryState({
        projectId: "project",
        searchParams: params,
        experiments,
        allLoggedMetricNames: names,
      });
      useEffect(() => {
        state = value;
      }, [value]);
      return null;
    }
    await render(h(State));
    await settle();
    expect(state.scalarPage).toBe(3);
    expect(state.scalarPageSize).toBe(24);
    await act(async () => state.toggleMetric("loss00"));
    expect(state.scalarPage).toBe(1);
    await act(async () => state.handleRestoreSavedView("page=2&pageSize=48"));
    expect(state.currentQueryString).toContain("page=2");
    expect(state.scalarPageSize).toBe(48);
  });
});
