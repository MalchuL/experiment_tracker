import type { HparamsDocument } from "@/domain/experiments/types";

export interface HparamsCompareItem {
  experimentId: string;
  experimentName: string;
  hparams: HparamsDocument | null;
}

export interface HparamsCompareResponse {
  projectId: string;
  experiments: HparamsCompareItem[];
}
