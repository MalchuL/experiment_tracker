import { useQuery } from "@tanstack/react-query";
import { QUERY_KEYS } from "@/lib/constants/query-keys";
import { scalarsService } from "../services";

export function useProjectScalarNames(projectId?: string): {
  scalarNames: string[];
  isLoading: boolean;
} {
  const { data, isLoading } = useQuery({
    queryKey: projectId ? [QUERY_KEYS.SCALARS.NAMES(projectId)] : [],
    queryFn: () => scalarsService.getNamesByProject(projectId!),
    enabled: !!projectId,
  });

  return {
    scalarNames: data?.scalar_names ?? [],
    isLoading,
  };
}
