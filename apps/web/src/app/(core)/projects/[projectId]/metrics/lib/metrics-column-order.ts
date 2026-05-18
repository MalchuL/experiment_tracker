export function buildByNameForRow(
  values: (number | null)[],
  apiMetricNames: string[],
  baseNames: string[]
): Record<string, number | null> {
  const indexByApi = new Map(apiMetricNames.map((n, i) => [n, i]));
  const byName: Record<string, number | null> = {};
  for (const n of baseNames) {
    const i = indexByApi.get(n);
    byName[n] = i === undefined ? null : (values[i] ?? null);
  }
  return byName;
}
