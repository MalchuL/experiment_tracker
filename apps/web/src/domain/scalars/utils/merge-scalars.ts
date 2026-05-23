import type {
  ExperimentScalarsPoints,
  ScalarSeries,
  ScalarsPointsResult,
} from "@/domain/scalars/types";

export function mergeExperimentScalars(
  current: ExperimentScalarsPoints,
  incoming: ExperimentScalarsPoints,
  options: { maxPoints?: number } = {}
): ExperimentScalarsPoints {
  const scalars: ExperimentScalarsPoints["scalars"] = { ...current.scalars };
  for (const [name, series] of Object.entries(incoming.scalars)) {
    scalars[name] = mergeSeries(scalars[name], series, options.maxPoints);
  }
  return {
    ...current,
    scalars,
    tags: incoming.tags ?? current.tags,
  };
}

/**
 * Merge an incremental scalar payload into one cached React Query page.
 *
 * Applies to both scalar live polling and the scalars page manual refresh button because both
 * paths call ``refreshChangedScalars`` in ``useScalarsLiveRefresh``. For each metric series, the
 * merge first replaces duplicate steps with incoming values, then thins the combined sampled points
 * across the step range while always retaining the newest step. This avoids letting a dense
 * incremental payload evict most of the already-sampled history.
 */
export function mergeScalarsPage(
  page: ScalarsPointsResult,
  incoming: ExperimentScalarsPoints[],
  options: { appendMissing?: boolean; maxPoints?: number } = {}
): ScalarsPointsResult {
  const incomingByExperiment = new Map(incoming.map((item) => [item.experiment_id, item]));
  const currentExperimentIds = new Set(page.data.map((item) => item.experiment_id));
  const missingIncoming = options.appendMissing
    ? incoming.filter((item) => !currentExperimentIds.has(item.experiment_id))
    : [];

  return {
    ...page,
    data: [
      ...missingIncoming.map((item) => sampleExperimentScalars(item, options.maxPoints)),
      ...page.data.map((current) => {
        const next = incomingByExperiment.get(current.experiment_id);
        return next ? mergeExperimentScalars(current, next, options) : current;
      }),
    ],
  };
}

function sampleExperimentScalars(
  item: ExperimentScalarsPoints,
  maxPoints?: number
): ExperimentScalarsPoints {
  return {
    ...item,
    scalars: Object.fromEntries(
      Object.entries(item.scalars).map(([name, series]) => [name, sampleSeries(series, maxPoints)])
    ),
  };
}

function mergeSeries(
  current: ScalarSeries | undefined,
  incoming: ScalarSeries,
  maxPoints?: number
): ScalarSeries {
  if (!current) {
    return sampleSeries(incoming, maxPoints);
  }
  const byStep = new Map<number, number>();
  current.x.forEach((step, index) => {
    const value = current.y[index];
    if (value !== undefined) byStep.set(step, value);
  });
  incoming.x.forEach((step, index) => {
    const value = incoming.y[index];
    if (value !== undefined) byStep.set(step, value);
  });
  const steps = sampleStepsByCoverage(Array.from(byStep.keys()), maxPoints);
  return {
    x: steps,
    y: steps.map((step) => byStep.get(step) ?? 0),
  };
}

function sampleSeries(series: ScalarSeries, maxPoints?: number): ScalarSeries {
  const byStep = new Map<number, number>();
  series.x.forEach((step, index) => {
    const value = series.y[index];
    if (value !== undefined) byStep.set(step, value);
  });
  const steps = sampleStepsByCoverage(Array.from(byStep.keys()), maxPoints);
  return {
    x: steps,
    y: steps.map((step) => byStep.get(step) ?? 0),
  };
}

function sampleStepsByCoverage(steps: number[], maxPoints?: number): number[] {
  const sortedSteps = [...steps].sort((a, b) => a - b);
  if (!maxPoints || maxPoints < 1 || sortedSteps.length <= maxPoints) {
    return sortedSteps;
  }

  const firstStep = sortedSteps[0]!;
  const latestStep = sortedSteps[sortedSteps.length - 1]!;
  if (maxPoints === 1) {
    return [latestStep];
  }

  const selected = new Set<number>([firstStep, latestStep]);
  const span = latestStep - firstStep;
  if (span <= 0) {
    return Array.from(selected).sort((a, b) => a - b);
  }

  let cursor = 0;
  for (let slot = 1; slot < maxPoints - 1; slot += 1) {
    const target = firstStep + (span * slot) / (maxPoints - 1);
    while (
      cursor < sortedSteps.length - 2 &&
      Math.abs(sortedSteps[cursor + 1]! - target) <= Math.abs(sortedSteps[cursor]! - target)
    ) {
      cursor += 1;
    }
    selected.add(sortedSteps[cursor]!);
  }

  if (selected.size < maxPoints) {
    for (let slot = 0; slot < maxPoints && selected.size < maxPoints; slot += 1) {
      const index = Math.round((slot * (sortedSteps.length - 1)) / (maxPoints - 1));
      selected.add(sortedSteps[index]!);
    }
  }

  if (selected.size < maxPoints) {
    for (const step of sortedSteps) {
      if (selected.size >= maxPoints) break;
      selected.add(step);
    }
  }

  return Array.from(selected).sort((a, b) => a - b);
}
