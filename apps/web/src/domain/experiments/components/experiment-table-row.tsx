"use client";

import { useSortable } from "@dnd-kit/sortable";
import { CSS } from "@dnd-kit/utilities";
import { TableCell, TableRow } from "@/components/ui/table";
import { StatusBadge } from "@/components/shared/status-badge";
import { GripVertical } from "lucide-react";
import { Experiment } from "../types";
import { ProjectMetric } from "@/domain/projects/types";
import { format } from "date-fns";

interface ExperimentTableRowProps {
    experiment: Experiment;
    onClick: () => void;
    projectMetrics?: ProjectMetric[];
    expMetrics?: Record<string, number | null>;
    parentName?: string;
}

export function ExperimentTableRow({
    experiment,
    onClick,
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
    };

    const formatMetricValue = (value: number | null | undefined): string => {
        if (value === null || value === undefined) return "NaN";
        return value.toFixed(4);
    };

    return (
        <TableRow
            ref={setNodeRef}
            style={style}
            className="cursor-pointer hover-elevate"
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
                    <div>
                        <p className="font-medium truncate">{experiment.name}</p>
                        {experiment.description && (
                            <p className="text-xs text-muted-foreground truncate max-w-[200px]">
                                {experiment.description}
                            </p>
                        )}
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
                <TableCell key={metric.name} className="text-right font-mono text-sm">
                    {formatMetricValue(expMetrics?.[metric.name])}
                </TableCell>
            ))}
            <TableCell className="text-muted-foreground text-sm">
                {format(new Date(experiment.createdAt), "MMM d")}
            </TableCell>
        </TableRow>
    );
}


