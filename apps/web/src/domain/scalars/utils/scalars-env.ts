const DEFAULT_MAX_POINTS_PER_PLOT = 1000;
const DEFAULT_DOT_THRESHOLD = 10;

function readPositiveInteger(value: string | undefined, fallback: number): number {
  const parsed = Number(value);
  if (!Number.isFinite(parsed) || parsed < 1) {
    return fallback;
  }
  return Math.floor(parsed);
}

export function getScalarsMaxPointsPerPlot(): number {
  return readPositiveInteger(
    process.env.NEXT_PUBLIC_SCALARS_MAX_POINTS_PER_PLOT,
    DEFAULT_MAX_POINTS_PER_PLOT
  );
}

export function getScalarsDotThreshold(): number {
  return readPositiveInteger(
    process.env.NEXT_PUBLIC_SCALARS_DOT_THRESHOLD,
    DEFAULT_DOT_THRESHOLD
  );
}
