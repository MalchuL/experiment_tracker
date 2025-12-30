export const HypothesisStatus = {
    PROPOSED: "proposed",
    TESTING: "testing",
    SUPPORTED: "supported",
    REFUTED: "refuted",
    INCONCLUSIVE: "inconclusive",
  } as const;
  
export type HypothesisStatusType = typeof HypothesisStatus[keyof typeof HypothesisStatus];

export interface Hypothesis {
    id: string;
    projectId: string;
    title: string;
    description: string;
    author: string;
    status: HypothesisStatusType;
    targetMetrics: string[];
    baseline: string;
    createdAt: string;
    updatedAt: string;
  }