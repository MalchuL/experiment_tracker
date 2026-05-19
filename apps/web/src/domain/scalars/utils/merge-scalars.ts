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
  const steps = reservoirSampleSteps(Array.from(byStep.keys()), maxPoints).sort((a, b) => a - b);
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
  const steps = reservoirSampleSteps(Array.from(byStep.keys()), maxPoints).sort((a, b) => a - b);
  return {
    x: steps,
    y: steps.map((step) => byStep.get(step) ?? 0),
  };
}

function reservoirSampleSteps(steps: number[], maxPoints?: number): number[] {
  const sortedSteps = [...steps].sort((a, b) => a - b);
  if (!maxPoints || maxPoints < 1 || sortedSteps.length <= maxPoints) {
    return sortedSteps;
  }

  const latestStep = sortedSteps[sortedSteps.length - 1]!;
  if (maxPoints === 1) {
    return [latestStep];
  }

  const reservoirSize = maxPoints - 1;
  const candidates = sortedSteps.slice(0, -1);
  const reservoir = candidates.slice(0, reservoirSize);
  const random = createSeededRandom(hashSteps(sortedSteps));

  for (let index = reservoirSize; index < candidates.length; index += 1) {
    const replacementIndex = Math.floor(random() * (index + 1));
    if (replacementIndex < reservoirSize) {
      reservoir[replacementIndex] = candidates[index]!;
    }
  }

  return [...reservoir, latestStep];
}

function createSeededRandom(seed: number): () => number {
  let state = seed || 0x6d2b79f5;
  return () => {
    state = (Math.imul(state, 1664525) + 1013904223) >>> 0;
    return state / 0x100000000;
  };
}

function hashSteps(steps: number[]): number {
  return steps.reduce((hash, step) => {
    const normalizedStep = Number.isFinite(step) ? Math.trunc(step) : 0;
    return Math.imul(hash ^ normalizedStep, 16777619) >>> 0;
  }, 2166136261);
}
