import type { PaginationParams } from "@/lib/types/pagination";

export function appendPaginationParams(
  path: string,
  params?: PaginationParams,
): string {
  if (params?.limit === undefined && params?.offset === undefined) {
    return path;
  }

  const searchParams = new URLSearchParams();
  if (params?.limit !== undefined) {
    searchParams.set("limit", String(params.limit));
  }
  if (params?.offset !== undefined) {
    searchParams.set("offset", String(params.offset));
  }

  const query = searchParams.toString();
  if (!query) {
    return path;
  }

  return `${path}${path.includes("?") ? "&" : "?"}${query}`;
}
