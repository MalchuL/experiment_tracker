export const SCALAR_PAGE_SIZES = [12, 24, 48] as const;
export function scalarPageSize(value: number): number {
  return SCALAR_PAGE_SIZES.includes(value as 12 | 24 | 48) ? value : 12;
}
export function scalarPage(value: number, total: number, size: number): number {
  return Math.min(Math.max(1, Math.ceil(total / size)), Math.max(1, Math.floor(value) || 1));
}
