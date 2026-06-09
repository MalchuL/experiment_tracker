import type { HparamsDocument } from "@/domain/experiments/types";

export interface HparamsListItem {
  experimentId: string;
  experimentName: string;
  hparams: HparamsDocument | null;
}

export interface HparamsListResponse {
  projectId: string;
  experiments: HparamsListItem[];
}
