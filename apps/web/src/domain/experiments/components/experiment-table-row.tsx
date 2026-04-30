"use client";

import { useSortable } from "@dnd-kit/sortable";
import { CSS } from "@dnd-kit/utilities";
import { TableCell, TableRow } from "@/components/ui/table";
import { StatusBadge } from "@/components/shared/status-badge";
import { GripVertical } from "lucide-react";
import { Experiment } from "../types";
import { ProjectMetric } from "@/domain/projects/types";
import { format } from "date-fns";
import { Metric } from "@/domain/metrics/types";
import { displayMetricKeyEquals, projectMetricKeyString } from "@/lib/metrics/format-metric-label";
import { getExperimentSelectionSurfaceStyle } from "../experiment-selection-style";
import { ExperimentTruncatedText } from "./experiment-truncated-text";

interface ExperimentTableRowProps {
    experiment: Experiment;
    onClick: () => void;
    isSelected?: boolean;
    projectMetrics?: ProjectMetric[];
    expMetrics?: Metric[];
    parentName?: string;
}

export function ExperimentTableRow({
    experiment,
    onClick,
    isSelected,
    projectMetrics,
    expMetrics,
    parentName,
}: ExperimentTableRowProps) {
    const {
        attributes,
        listeners,
        setNodeRef,
        transform,
        transition,
        isDragging,
    } = useSortable({ id: experiment.id });

    const style = {
        transform: CSS.Transform.toString(transform),
        transition,
        opacity: isDragging ? 0.5 : 1,
        ...(isSelected ? getExperimentSelectionSurfaceStyle(experiment.color) : {}),
    };

    const formatMetricValue = (value: number | null | undefined): string => {
        if (value === null || value === undefined) return "NaN";
        return value.toFixed(4);
    };

    return (
        <TableRow
            ref={setNodeRef}
            data-state={isSelected ? "selected" : undefined}
            style={style}
            className={
                isSelected
                    ? "cursor-pointer transition-colors hover-elevate"
                    : "cursor-pointer hover-elevate"
            }
            onClick={onClick}
            data-testid={`row-experiment-${experiment.id}`}
        >
            <TableCell>
                <div
                    className="cursor-grab active:cursor-grabbing p-1"
                    {...attributes}
                    {...listeners}
                    onClick={(e) => e.stopPropagation()}
                >
                    <GripVertical className="w-4 h-4 text-muted-foreground" />
                </div>
            </TableCell>
            <TableCell>
                <div className="flex items-center gap-2">
                    <div
                        className="w-3 h-3 rounded-full flex-shrink-0"
                        style={{ backgroundColor: experiment.color }}
                    />
                    <div className="min-w-0">
                        <ExperimentTruncatedText text={experiment.name} className="font-medium" />
                        {experiment.description ? (
                            <ExperimentTruncatedText
                                text={experiment.description}
                                className="mt-0.5 text-xs text-muted-foreground"
                            />
                        ) : null}
                    </div>
                </div>
            </TableCell>
            <TableCell>
                <StatusBadge status={experiment.status} />
            </TableCell>
            <TableCell className="text-muted-foreground text-sm">
                {parentName || "-"}
            </TableCell>
            {projectMetrics?.map((metric) => (
                <TableCell key={projectMetricKeyString(metric)} className="text-right font-mono text-sm">
                    {formatMetricValue(
                        expMetrics?.find((m) =>
                            displayMetricKeyEquals(
                                { name: m.name, label: m.label },
                                { name: metric.name, label: metric.label ?? null }
                            )
                        )?.value
                    )}
                </TableCell>
            ))}
            <TableCell className="text-muted-foreground text-sm">
                {format(new Date(experiment.createdAt), "MMM d")}
            </TableCell>
        </TableRow>
    );
}


