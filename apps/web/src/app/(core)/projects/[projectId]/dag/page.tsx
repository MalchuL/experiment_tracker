"use client";

import { ProjectDagView } from "@/domain/experiments/components/project-dag-view";

export default function DAGView() {
  return (
    <div className="h-full min-h-0 flex flex-col">
      <ProjectDagView />
    </div>
  );
}
