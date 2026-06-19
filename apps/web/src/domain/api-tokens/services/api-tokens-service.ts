import { serviceClients } from "@/lib/api/clients/axios-client";
import { appendPaginationParams, fetchAllPaginated } from "@/lib/api/pagination";
import { API_ROUTES } from "@/lib/constants/api-routes";
import { DEFAULT_PAGE_SIZE } from "@/lib/constants/pagination";
import type { PaginatedResponse } from "@/lib/types/pagination";
import type {
  ApiTokenCreateRequest,
  ApiTokenCreateResponse,
  ApiTokenListItem,
  ApiTokenUpdateRequest,
} from "../types";

export interface ApiTokensService {
  create: (payload: ApiTokenCreateRequest) => Promise<ApiTokenCreateResponse>;
  list: () => Promise<ApiTokenListItem[]>;
  update: (id: string, payload: ApiTokenUpdateRequest) => Promise<ApiTokenListItem>;
  revoke: (id: string) => Promise<void>;
}

export const apiTokensService: ApiTokensService = {
  create: async (payload) => {
    const response = await serviceClients.api.post<ApiTokenCreateResponse>(
      API_ROUTES.USERS.API_TOKENS.CREATE,
      payload,
    );
    return response.data;
  },
  list: async () => {
    return fetchAllPaginated(
      async (params) => {
        const response = await serviceClients.api.get<PaginatedResponse<ApiTokenListItem>>(
          appendPaginationParams(API_ROUTES.USERS.API_TOKENS.LIST, params),
        );
        return response.data;
      },
      { limit: DEFAULT_PAGE_SIZE },
    );
  },
  update: async (id, payload) => {
    const response = await serviceClients.api.patch<ApiTokenListItem>(
      API_ROUTES.USERS.API_TOKENS.BY_ID.UPDATE(id),
      payload,
    );
    return response.data;
  },
  revoke: async (id) => {
    await serviceClients.api.delete(API_ROUTES.USERS.API_TOKENS.BY_ID.DELETE(id));
  },
};
