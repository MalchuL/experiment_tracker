export interface PaginationParams {
  limit?: number;
  offset?: number;
}

export interface PaginatedResponse<T> {
  data: T[];
  hasNext: boolean;
  size: number;
  total: number;
}
