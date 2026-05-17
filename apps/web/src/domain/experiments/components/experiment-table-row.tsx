"use client";

import { useSortable } from "@dnd-kit/sortable";
import { CSS } from "@dnd-kit/utilities";
import { TableCell, TableRow } from "@/components/ui/table";
import { StatusBadge } from "@/components/shared/status-badge";
import { GripVertical } from "lucide-react";
import { Experiment } from "../types";
import { ProjectMetric } from "@/domain/projects/types";
import { format, parseISO } from "date-fns";
import { Metric } from "@/domain/metrics/types";
import { displayMetricKeyEquals, projectMetricKeyString } from "@/lib/metrics/format-metric-label";
import {
  formatMetricScalarForDisplay,
  formatMetricScalarTooltipFull,
} from "@/lib/metrics/metric-value-display";
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
            <TableCell className="min-w-0 max-w-[10rem] w-[10rem] text-muted-foreground text-sm sm:max-w-[14rem] sm:w-[14rem]">
                {parentName ? (
                    <ExperimentTruncatedText
                        text={parentName}
                        as="span"
                        showTooltip="always"
                        lineClamp={1}
                    />
                ) : (
                    "-"
                )}
            </TableCell>
            {projectMetrics?.map((metric) => {
                const raw = expMetrics?.find((m) =>
                    displayMetricKeyEquals(
                        { name: m.name, label: m.label },
                        { name: metric.name, label: metric.label ?? null }
                    )
                )?.value;
                return (
                    <TableCell key={projectMetricKeyString(metric)} className="text-right font-mono text-sm">
                        <span
                            className="inline-block min-w-0 max-w-full cursor-default text-right tabular-nums"
                            title={formatMetricScalarTooltipFull(raw)}
                        >
                            {formatMetricScalarForDisplay(raw)}
                        </span>
                    </TableCell>
                );
            })}
            <TableCell className="text-muted-foreground text-sm whitespace-nowrap tabular-nums">
                {format(parseISO(experiment.createdAt), "MMM d, yyyy, HH:mm")}
            </TableCell>
        </TableRow>
    );
}


