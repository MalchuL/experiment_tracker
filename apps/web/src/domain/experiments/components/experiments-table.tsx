"use client";

import {
    DndContext,
    DragEndEvent,
    PointerSensor,
    useSensor,
    useSensors,
    closestCenter,
} from "@dnd-kit/core";
import {
    SortableContext,
    verticalListSortingStrategy,
} from "@dnd-kit/sortable";
import { Card } from "@/components/ui/card";
import {
    Table,
    TableBody,
    TableHead,
    TableHeader,
    TableRow,
} from "@/components/ui/table";
import { TrendingUp, TrendingDown } from "lucide-react";
import { Experiment } from "../types";
import { ProjectMetric } from "@/domain/projects/types";
import { ExperimentTableRow } from "./experiment-table-row";
import { arrayMove } from "@dnd-kit/sortable";

interface ExperimentsTableProps {
    experiments: Experiment[];
    projectMetrics?: ProjectMetric[];
    aggregatedMetrics?: Record<string, Record<string, number | null>>;
    onExperimentClick: (experimentId: string) => void;
    onReorder: (experimentIds: string[]) => void;
}

export function ExperimentsTable({
    experiments,
    projectMetrics,
    aggregatedMetrics,
    onExperimentClick,
    onReorder,
}: ExperimentsTableProps) {
    const sensors = useSensors(
        useSensor(PointerSensor, {
            activationConstraint: {
                distance: 8,
            },
        })
    );

    const handleDragEnd = (event: DragEndEvent) => {
        const { active, over } = event;
        if (!over || active.id === over.id) return;

        const oldIndex = experiments.findIndex((e) => e.id === active.id);
        const newIndex = experiments.findIndex((e) => e.id === over.id);

        const newOrder = arrayMove(experiments, oldIndex, newIndex);
        onReorder(newOrder.map((e) => e.id));
    };

    // Filter metrics by displayMetrics setting (this should come from project settings)
    const filteredMetrics = projectMetrics || [];

    return (
        <Card>
            <DndContext
                sensors={sensors}
                collisionDetection={closestCenter}
                onDragEnd={handleDragEnd}
            >
                <Table>
                    <TableHeader>
                        <TableRow>
                            <TableHead className="w-[40px]"></TableHead>
                            <TableHead className="w-[200px]">Experiment</TableHead>
                            <TableHead>Status</TableHead>
                            <TableHead>Parent</TableHead>
                            {filteredMetrics.map((metric) => (
                                <TableHead key={metric.name} className="text-right">
                                    <div className="flex items-center justify-end gap-1">
                                        {metric.name}
                                        {metric.direction === "minimize" ? (
                                            <TrendingDown className="w-3 h-3" />
                                        ) : (
                                            <TrendingUp className="w-3 h-3" />
                                        )}
                                    </div>
                                </TableHead>
                            ))}
                            <TableHead className="w-[80px]">Created</TableHead>
                        </TableRow>
                    </TableHeader>
                    <SortableContext
                        items={experiments.map((e) => e.id)}
                        strategy={verticalListSortingStrategy}
                    >
                        <TableBody>
                            {experiments.map((experiment) => {
                                const parent = experiments.find(
                                    (e) => e.id === experiment.parentExperimentId
                                );
                                return (
                                    <ExperimentTableRow
                                        key={experiment.id}
                                        experiment={experiment}
                                        onClick={() => onExperimentClick(experiment.id)}
                                        projectMetrics={filteredMetrics}
                                        expMetrics={aggregatedMetrics?.[experiment.id]}
                                        parentName={parent?.name}
                                    />
                                );
                            })}
                        </TableBody>
                    </SortableContext>
                </Table>
            </DndContext>
        </Card>
    );
}


