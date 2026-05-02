import type {
  ExperimentScalarsPoints,
  ScalarSeries,
  ScalarsPointsResult,
} from "@/domain/scalars/types";

export function mergeExperimentScalars(
  current: ExperimentScalarsPoints,
  incoming: ExperimentScalarsPoints
): ExperimentScalarsPoints {
  const scalars: ExperimentScalarsPoints["scalars"] = { ...current.scalars };
  for (const [name, series] of Object.entries(incoming.scalars)) {
    scalars[name] = mergeSeries(scalars[name], series);
  }
  return {
    ...current,
    scalars,
    tags: incoming.tags ?? current.tags,
  };
}

export function mergeScalarsPage(
  page: ScalarsPointsResult,
  incoming: ExperimentScalarsPoints[]
): ScalarsPointsResult {
  const incomingByExperiment = new Map(incoming.map((item) => [item.experiment_id, item]));
  return {
    ...page,
    data: page.data.map((current) => {
      const next = incomingByExperiment.get(current.experiment_id);
      return next ? mergeExperimentScalars(current, next) : current;
    }),
  };
}

function mergeSeries(current: ScalarSeries | undefined, incoming: ScalarSeries): ScalarSeries {
  if (!current) {
    return incoming;
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
  const steps = Array.from(byStep.keys()).sort((a, b) => a - b);
  return {
    x: steps,
    y: steps.map((step) => byStep.get(step) ?? 0),
  };
}
