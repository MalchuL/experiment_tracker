"use client";

import { ProjectMetric } from "@/domain/projects/types";

interface ExperimentSidebarProps {
    experimentId: string;
    onClose: () => void;
    projectMetrics?: ProjectMetric[];
    aggregatedMetrics?: Record<string, number | null>;
}

export function ExperimentSidebar({
    experimentId,
    onClose,
    projectMetrics,
    aggregatedMetrics,
}: ExperimentSidebarProps) {
    // TODO: Implement experiment sidebar details view
    return (
        <div className="fixed right-0 top-0 h-full w-96 bg-background border-l shadow-lg p-6">
            <div className="flex items-center justify-between mb-4">
                <h2 className="text-lg font-semibold">Experiment Details</h2>
                <button onClick={onClose} className="text-muted-foreground hover:text-foreground">
                    ×
                </button>
            </div>
            <p className="text-sm text-muted-foreground">Experiment ID: {experimentId}</p>
            {/* Add experiment details here */}
        </div>
    );
}


