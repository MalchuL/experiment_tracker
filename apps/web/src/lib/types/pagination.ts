export interface PaginationParams {
  limit?: number;
  offset?: number;
  /** Server-side substring on experiment id, name, and description (GET …/experiments?search=). */
  search?: string;
}

export interface PaginatedResponse<T> {
  data: T[];
  hasNext: boolean;
  size: number;
  total: number;
}
