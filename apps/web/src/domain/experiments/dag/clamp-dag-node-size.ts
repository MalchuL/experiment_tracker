import { DAG_NODE_MIN_WIDTH_PX } from "@/lib/constants/dag";

export function clampDagNodeWidth(width: number): number {
  return Math.round(Math.max(DAG_NODE_MIN_WIDTH_PX, width));
}
