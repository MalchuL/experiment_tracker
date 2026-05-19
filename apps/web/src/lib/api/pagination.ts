import type { PaginationParams } from "@/lib/types/pagination";

export function appendPaginationParams(
  path: string,
  params?: PaginationParams,
): string {
  if (
    params?.limit === undefined &&
    params?.offset === undefined &&
    params?.search === undefined &&
    params?.includeFeatures === undefined
  ) {
    return path;
  }

  const searchParams = new URLSearchParams();
  if (params?.limit !== undefined) {
    searchParams.set("limit", String(params.limit));
  }
  if (params?.offset !== undefined) {
    searchParams.set("offset", String(params.offset));
  }
  if (params?.search !== undefined && params.search.trim() !== "") {
    searchParams.set("search", params.search.trim());
  }
  if (params?.includeFeatures !== undefined) {
    searchParams.set("includeFeatures", String(params.includeFeatures));
  }

  const query = searchParams.toString();
  if (!query) {
    return path;
  }

  return `${path}${path.includes("?") ? "&" : "?"}${query}`;
}
