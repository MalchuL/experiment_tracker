import type { PaginatedResponse, PaginationParams } from "@/lib/types/pagination";

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

export async function fetchAllPaginated<T>(
  fetchPage: (params: Required<Pick<PaginationParams, "limit" | "offset">>) => Promise<PaginatedResponse<T>>,
  options?: { limit?: number; offset?: number },
): Promise<T[]> {
  const limit = options?.limit ?? 100;
  let offset = options?.offset ?? 0;
  const items: T[] = [];

  while (true) {
    const page = await fetchPage({ limit, offset });
    items.push(...page.data);

    if (!page.hasNext) {
      return items;
    }

    offset += page.size > 0 ? page.size : limit;
  }
}
