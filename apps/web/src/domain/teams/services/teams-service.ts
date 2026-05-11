import { serviceClients } from "@/lib/api/clients/axios-client";
import { appendPaginationParams } from "@/lib/api/pagination";
import { API_ROUTES } from "@/lib/constants/api-routes";
import type { PaginatedResponse, PaginationParams } from "@/lib/types/pagination";
import type { CategoryCleanupResponse } from "@/domain/experiments/types";
import type { Team, TeamListItem, TeamMemberRow, TeamMemberWritePayload } from "../types";

export interface TeamsService {
  list: (params?: PaginationParams) => Promise<PaginatedResponse<TeamListItem>>;
  getById: (teamId: string) => Promise<Team>;
  listMembers: (teamId: string) => Promise<TeamMemberRow[]>;
  create: (data: { name: string; description?: string | null }) => Promise<Team>;
  update: (data: { id: string; name: string; description?: string | null }) => Promise<Team>;
  delete: (teamId: string) => Promise<CategoryCleanupResponse>;
  addMember: (payload: TeamMemberWritePayload) => Promise<TeamMemberRow>;
  updateMember: (payload: TeamMemberWritePayload) => Promise<TeamMemberRow>;
  removeMember: (userId: string, teamId: string) => Promise<void>;
  lookupUser: (teamId: string, email: string) => Promise<{ id: string; email: string | null; displayName: string | null }>;
}

export const teamsService: TeamsService = {
  list: async (params) => {
    const response = await serviceClients.api.get<PaginatedResponse<TeamListItem>>(
      appendPaginationParams(API_ROUTES.TEAMS.LIST, params),
    );
    return response.data;
  },
  getById: async (teamId) => {
    const response = await serviceClients.api.get<Team>(API_ROUTES.TEAMS.BY_ID.GET(teamId));
    return response.data;
  },
  listMembers: async (teamId) => {
    const response = await serviceClients.api.get<TeamMemberRow[]>(
      API_ROUTES.TEAMS.BY_ID.MEMBERS(teamId),
    );
    return response.data;
  },
  create: async (data) => {
    const response = await serviceClients.api.post<Team>(API_ROUTES.TEAMS.CREATE, data);
    return response.data;
  },
  update: async (data) => {
    const response = await serviceClients.api.patch<Team>(API_ROUTES.TEAMS.PATCH, data);
    return response.data;
  },
  delete: async (teamId) => {
    const response = await serviceClients.api.delete<CategoryCleanupResponse>(API_ROUTES.TEAMS.BY_ID.DELETE(teamId));
    return response.data;
  },
  addMember: async (payload) => {
    const response = await serviceClients.api.post<TeamMemberRow>(
      API_ROUTES.TEAMS.MEMBERS.ADD,
      payload,
    );
    return response.data;
  },
  updateMember: async (payload) => {
    const response = await serviceClients.api.patch<TeamMemberRow>(
      API_ROUTES.TEAMS.MEMBERS.PATCH,
      payload,
    );
    return response.data;
  },
  removeMember: async (userId, teamId) => {
    await serviceClients.api.delete(API_ROUTES.TEAMS.MEMBERS.DELETE, {
      data: { userId, teamId },
    });
  },
  lookupUser: async (teamId, email) => {
    const response = await serviceClients.api.get<{
      id: string;
      email: string | null;
      displayName: string | null;
    }>(API_ROUTES.TEAMS.BY_ID.USERS_LOOKUP(teamId), { params: { email } });
    return response.data;
  },
};
