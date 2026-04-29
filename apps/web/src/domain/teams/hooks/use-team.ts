import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { teamsService } from "@/domain/teams/services";
import { QUERY_KEYS } from "@/lib/constants/query-keys";

export function useTeam(teamId: string | undefined) {
  return useQuery({
    queryKey: [QUERY_KEYS.TEAMS.GET_BY_ID(teamId ?? "")],
    queryFn: () => teamsService.getById(teamId!),
    enabled: Boolean(teamId),
  });
}

export function useTeamMembers(teamId: string | undefined) {
  return useQuery({
    queryKey: [QUERY_KEYS.TEAMS.MEMBERS(teamId ?? "")],
    queryFn: () => teamsService.listMembers(teamId!),
    enabled: Boolean(teamId),
  });
}

export function useAddTeamMember(teamId: string | undefined) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: teamsService.addMember,
    onSuccess: () => {
      if (teamId) {
        void qc.invalidateQueries({ queryKey: [QUERY_KEYS.TEAMS.MEMBERS(teamId)] });
        void qc.invalidateQueries({ queryKey: [QUERY_KEYS.TEAMS.LIST] });
      }
    },
  });
}

export function useUpdateTeamMember(teamId: string | undefined) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: teamsService.updateMember,
    onSuccess: () => {
      if (teamId) {
        void qc.invalidateQueries({ queryKey: [QUERY_KEYS.TEAMS.MEMBERS(teamId)] });
      }
    },
  });
}

export function useRemoveTeamMember(teamId: string | undefined) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ userId, teamId: tid }: { userId: string; teamId: string }) =>
      teamsService.removeMember(userId, tid),
    onSuccess: (_, v) => {
      void qc.invalidateQueries({ queryKey: [QUERY_KEYS.TEAMS.MEMBERS(v.teamId)] });
      void qc.invalidateQueries({ queryKey: [QUERY_KEYS.TEAMS.LIST] });
    },
  });
}
