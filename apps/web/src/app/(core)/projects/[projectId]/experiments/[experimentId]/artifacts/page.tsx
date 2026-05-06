import { redirect } from "next/navigation";
import { buildExperimentDetailsHref } from "@/lib/experiment-details-url";

export default async function ExperimentArtifactsRedirectPage({
  params,
}: {
  params: Promise<{ projectId: string; experimentId: string }>;
}) {
  const { projectId, experimentId } = await params;
  redirect(buildExperimentDetailsHref(projectId, [experimentId]));
}
