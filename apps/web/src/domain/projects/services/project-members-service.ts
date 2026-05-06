import { serviceClients } from "@/lib/api/clients/axios-client";
import { API_ROUTES } from "@/lib/constants/api-routes";
import type {
  ProjectMemberInvite,
  ProjectMemberRow,
  UserLookupResult,
} from "../types/members";

export interface ProjectMembersService {
  list: (projectId: string) => Promise<ProjectMemberRow[]>;
  lookupUser: (projectId: string, email: string) => Promise<UserLookupResult>;
  invite: (projectId: string, body: ProjectMemberInvite) => Promise<ProjectMemberRow>;
  updateRole: (projectId: string, userId: string, role: ProjectMemberInvite["role"]) => Promise<ProjectMemberRow>;
  remove: (projectId: string, userId: string) => Promise<void>;
}

export const projectMembersService: ProjectMembersService = {
  list: async (projectId) => {
    const response = await serviceClients.api.get<ProjectMemberRow[]>(
      API_ROUTES.PROJECTS.BY_ID.MEMBERS(projectId),
    );
    return response.data;
  },
  lookupUser: async (projectId, email) => {
    const response = await serviceClients.api.get<UserLookupResult>(
      API_ROUTES.PROJECTS.BY_ID.USERS_LOOKUP(projectId),
      { params: { email } },
    );
    return response.data;
  },
  invite: async (projectId, body) => {
    const response = await serviceClients.api.post<ProjectMemberRow>(
      API_ROUTES.PROJECTS.BY_ID.MEMBERS(projectId),
      body,
    );
    return response.data;
  },
  updateRole: async (projectId, userId, role) => {
    const response = await serviceClients.api.patch<ProjectMemberRow>(
      API_ROUTES.PROJECTS.BY_ID.MEMBERS(projectId),
      { userId, role },
    );
    return response.data;
  },
  remove: async (projectId, userId) => {
    await serviceClients.api.delete(API_ROUTES.PROJECTS.BY_ID.MEMBERS(projectId), {
      data: { userId },
    });
  },
};
