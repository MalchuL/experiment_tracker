export function closestStep(target: number, steps: number[]): number | null {
  if (steps.length === 0) return null;
  let best = steps[0];
  let bestDist = Math.abs(best - target);
  for (let i = 1; i < steps.length; i += 1) {
    const dist = Math.abs(steps[i] - target);
    if (dist < bestDist) {
      best = steps[i];
      bestDist = dist;
    }
  }
  return best;
}
