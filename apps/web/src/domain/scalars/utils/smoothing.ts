export function applySmoothing(data: number[], weight: number): number[] {
  if (weight === 0 || data.length === 0) return data;
  const smoothed: number[] = [];
  let last = data[0];
  for (const value of data) {
    const smoothedValue = last * weight + value * (1 - weight);
    smoothed.push(smoothedValue);
    last = smoothedValue;
  }
  return smoothed;
}
