import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { projectMembersService } from "../services/project-members-service";
import { QUERY_KEYS } from "@/lib/constants/query-keys";
import type { ProjectMemberInvite, ProjectMemberRole } from "../types/members";

export function useProjectMembers(projectId: string | undefined) {
  return useQuery({
    queryKey: [QUERY_KEYS.PROJECT_MEMBERS.LIST(projectId ?? "")],
    queryFn: () => projectMembersService.list(projectId!),
    enabled: Boolean(projectId),
  });
}

export function useInviteProjectMember(projectId: string | undefined) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: ProjectMemberInvite) =>
      projectMembersService.invite(projectId!, body),
    onSuccess: () => {
      if (projectId) {
        void qc.invalidateQueries({ queryKey: [QUERY_KEYS.PROJECT_MEMBERS.LIST(projectId)] });
      }
    },
  });
}

export function useUpdateProjectMemberRole(projectId: string | undefined) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ userId, role }: { userId: string; role: ProjectMemberRole }) =>
      projectMembersService.updateRole(projectId!, userId, role),
    onSuccess: () => {
      if (projectId) {
        void qc.invalidateQueries({ queryKey: [QUERY_KEYS.PROJECT_MEMBERS.LIST(projectId)] });
      }
    },
  });
}

export function useRemoveProjectMember(projectId: string | undefined) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (userId: string) => projectMembersService.remove(projectId!, userId),
    onSuccess: () => {
      if (projectId) {
        void qc.invalidateQueries({ queryKey: [QUERY_KEYS.PROJECT_MEMBERS.LIST(projectId)] });
      }
    },
  });
}

export function useLookupProjectUser(projectId: string | undefined) {
  return useMutation({
    mutationFn: (email: string) => projectMembersService.lookupUser(projectId!, email),
  });
}
