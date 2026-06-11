export interface PaginationParams {
  limit?: number;
  offset?: number;
  /** Server-side substring on experiment id, name, description, and tags (GET …/experiments?search=). */
  search?: string;
  /** Opt into heavy feature-tree payloads on experiment list endpoints. */
  includeFeatures?: boolean;
}

export interface PaginatedResponse<T> {
  data: T[];
  hasNext: boolean;
  size: number;
  total: number;
}
