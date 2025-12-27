import { useRoute } from "wouter";

export function useProjectId(): string | null {
  const [, params] = useRoute("/projects/:id/*?");
  const [, detailParams] = useRoute("/projects/:id");
  
  return params?.id || detailParams?.id || null;
}
