"use client";

import { useParams } from "next/navigation";
import { CompareShell } from "@/domain/compare/components/compare-shell";

export default function ComparePage() {
  const { projectId } = useParams<{ projectId: string }>();
  return <CompareShell projectId={projectId} />;
}
