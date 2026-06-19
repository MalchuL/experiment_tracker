import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { teamsService } from "@/domain/teams/services";
import { QUERY_KEYS } from "@/lib/constants/query-keys";

export function useTeams() {
  return useQuery({
    queryKey: [QUERY_KEYS.TEAMS.LIST],
    queryFn: () => teamsService.listAll(),
  });
}

export function useCreateTeam() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: teamsService.create,
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: [QUERY_KEYS.TEAMS.LIST] });
    },
  });
}

export function useUpdateTeam() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: teamsService.update,
    onSuccess: (_, v) => {
      void qc.invalidateQueries({ queryKey: [QUERY_KEYS.TEAMS.LIST] });
      void qc.invalidateQueries({ queryKey: [QUERY_KEYS.TEAMS.GET_BY_ID(v.id)] });
    },
  });
}

export function useDeleteTeam() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: teamsService.delete,
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: [QUERY_KEYS.TEAMS.LIST] });
    },
  });
}
