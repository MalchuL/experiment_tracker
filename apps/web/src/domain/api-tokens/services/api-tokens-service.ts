import { serviceClients } from "@/lib/api/clients/axios-client";
import { API_ROUTES } from "@/lib/constants/api-routes";
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
    const response = await serviceClients.api.get<ApiTokenListItem[]>(
      API_ROUTES.USERS.API_TOKENS.LIST,
    );
    return response.data;
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
