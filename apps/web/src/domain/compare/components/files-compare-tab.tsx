"use client";

import { useEffect, useMemo, useState } from "react";
import { keepPreviousData, useQuery } from "@tanstack/react-query";
import { ArrowLeftRight, GitBranch, MoreHorizontal } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import type { Experiment } from "@/domain/experiments/types";
import { QUERY_KEYS } from "@/lib/constants/query-keys";
import { cn } from "@/lib/utils";
import { compareService } from "../service";
import type { ExperimentSnapshotFiles } from "../types";
import { FileCompareView } from "./file-compare-view";

interface FilesCompareTabProps {
  allExperiments: Experiment[];
  selectedExperiments: Experiment[];
  onEnsureExperimentSelected: (experimentId: string) => void;
}

const NONE_VALUE = "__none";

export function FilesCompareTab({
  allExperiments,
  selectedExperiments,
  onEnsureExperimentSelected,
}: FilesCompareTabProps) {
  const [leftExperimentId, setLeftExperimentId] = useState<string | null>(null);
  const [rightExperimentId, setRightExperimentId] = useState<string | null>(null);
  const [displayedLeft, setDisplayedLeft] = useState<ExperimentSnapshotFiles | null>(null);
  const [displayedRight, setDisplayedRight] = useState<ExperimentSnapshotFiles | null>(null);

  const experimentsById = useMemo(() => {
    return new Map(allExperiments.map((experiment) => [experiment.id, experiment]));
  }, [allExperiments]);

  const latestExperiment = allExperiments[0] ?? null;

  useEffect(() => {
    if (selectedExperiments.length === 0) {
      setLeftExperimentId(null);
      setRightExperimentId(null);
      return;
    }
    const selectedIds = new Set(selectedExperiments.map((experiment) => experiment.id));
    setLeftExperimentId((current) =>
      current && selectedIds.has(current) ? current : selectedExperiments[0]?.id ?? null
    );
    setRightExperimentId((current) => {
      if (current && selectedIds.has(current) && current !== selectedExperiments[0]?.id) {
        return current;
      }
      return selectedExperiments.find((experiment) => experiment.id !== selectedExperiments[0]?.id)
        ?.id ?? null;
    });
  }, [selectedExperiments]);

  const leftExperiment = leftExperimentId
    ? experimentsById.get(leftExperimentId) ?? selectedExperiments.find((e) => e.id === leftExperimentId)
    : null;
  const rightExperiment = rightExperimentId
    ? experimentsById.get(rightExperimentId) ?? selectedExperiments.find((e) => e.id === rightExperimentId)
    : null;
  const leftParentExperiment = leftExperiment?.parentExperimentId
    ? experimentsById.get(leftExperiment.parentExperimentId) ?? null
    : null;
  const rightParentExperiment = rightExperiment?.parentExperimentId
    ? experimentsById.get(rightExperiment.parentExperimentId) ?? null
    : null;

  const experimentIds = useMemo(() => {
    return [leftExperimentId, rightExperimentId]
      .filter((id): id is string => Boolean(id))
      .filter((id, index, ids) => ids.indexOf(id) === index);
  }, [leftExperimentId, rightExperimentId]);

  const query = useQuery({
    queryKey: [QUERY_KEYS.COMPARE.SNAPSHOT_FILES(experimentIds)],
    queryFn: () => compareService.getSnapshotFiles(experimentIds),
    enabled: Boolean(leftExperimentId),
    placeholderData: keepPreviousData,
  });

  const loadedLeft = query.data?.items.find((item) => item.experimentId === leftExperimentId);
  const loadedRight = rightExperimentId
    ? query.data?.items.find((item) => item.experimentId === rightExperimentId)
    : undefined;

  useEffect(() => {
    if (!leftExperimentId) {
      setDisplayedLeft(null);
      return;
    }

    if (loadedLeft) {
      setDisplayedLeft(loadedLeft);
    }
  }, [leftExperimentId, loadedLeft]);

  useEffect(() => {
    if (!rightExperimentId) {
      setDisplayedRight(null);
      return;
    }

    if (loadedRight) {
      setDisplayedRight(loadedRight);
    }
  }, [rightExperimentId, loadedRight]);

  if (experimentIds.length === 0) {
    return (
      <CenteredState className="flex-col gap-3 text-center">
        <span>
          Please select an experiment to browse its file snapshot
          {latestExperiment ? ", or choose the latest experiment." : "."}
        </span>
        {latestExperiment ? (
          <Button
            type="button"
            variant="outline"
            size="sm"
            onClick={() => {
              onEnsureExperimentSelected(latestExperiment.id);
              setLeftExperimentId(latestExperiment.id);
            }}
          >
            Choose {latestExperiment.name}
          </Button>
        ) : null}
      </CenteredState>
    );
  }

  if (query.isLoading && !displayedLeft) {
    return <CenteredState>Loading snapshots...</CenteredState>;
  }

  if (query.isError) {
    return <CenteredState>Failed to load snapshot files.</CenteredState>;
  }

  const left = loadedLeft ?? displayedLeft;
  const right = rightExperimentId ? loadedRight ?? displayedRight ?? undefined : undefined;

  const controls = (
    <FilesCompareControls
      selectedExperiments={selectedExperiments}
      leftExperimentId={leftExperimentId}
      rightExperimentId={rightExperimentId}
      leftParentExperiment={leftParentExperiment}
      rightParentExperiment={rightParentExperiment}
      onLeftChange={setLeftExperimentId}
      onRightChange={(experimentId) =>
        setRightExperimentId(experimentId === NONE_VALUE ? null : experimentId)
      }
      onUseLeftParentAsRight={(experimentId) => {
        onEnsureExperimentSelected(experimentId);
        setRightExperimentId(experimentId);
      }}
      onUseRightParentAsLeft={(experimentId) => {
        onEnsureExperimentSelected(experimentId);
        setLeftExperimentId(experimentId);
      }}
      onSwap={() => {
        if (!rightExperimentId) {
          return;
        }
        setLeftExperimentId(rightExperimentId);
        setRightExperimentId(leftExperimentId);
      }}
    />
  );

  if (!left?.snapshotId) {
    return (
      <div className="flex min-h-0 flex-1 flex-col">
        {controls}
        <CenteredState>
          The selected experiment needs a logged snapshot before files can be viewed.
        </CenteredState>
      </div>
    );
  }

  if (rightExperimentId && !right?.snapshotId) {
    return (
      <div className="flex min-h-0 flex-1 flex-col">
        {controls}
        <CenteredState>
          Both selected experiments need logged snapshots before files can be compared.
        </CenteredState>
      </div>
    );
  }

  return (
    <div className="flex min-h-0 flex-1 flex-col">
      {controls}
      <FileCompareView
        leftFiles={left.files}
        rightFiles={right?.files}
        leftLabel={leftExperiment?.name ?? leftExperimentId ?? "Left"}
        rightLabel={rightExperiment?.name ?? rightExperimentId ?? undefined}
        leftExperimentId={leftExperimentId ?? undefined}
        rightExperimentId={rightExperimentId ?? undefined}
        leftSnapshotId={left.snapshotId ?? undefined}
        rightSnapshotId={right?.snapshotId ?? undefined}
      />
    </div>
  );
}

function FilesCompareControls({
  selectedExperiments,
  leftExperimentId,
  rightExperimentId,
  leftParentExperiment,
  rightParentExperiment,
  onLeftChange,
  onRightChange,
  onUseLeftParentAsRight,
  onUseRightParentAsLeft,
  onSwap,
}: {
  selectedExperiments: Experiment[];
  leftExperimentId: string | null;
  rightExperimentId: string | null;
  leftParentExperiment: Experiment | null;
  rightParentExperiment: Experiment | null;
  onLeftChange: (experimentId: string) => void;
  onRightChange: (experimentId: string) => void;
  onUseLeftParentAsRight: (experimentId: string) => void;
  onUseRightParentAsLeft: (experimentId: string) => void;
  onSwap: () => void;
}) {
  return (
    <TooltipProvider delayDuration={250}>
      <div className="grid items-center gap-3 border-b bg-muted/20 px-4 py-2 md:grid-cols-[minmax(0,1fr)_auto_minmax(0,1fr)]">
        <div className="flex min-w-0 flex-wrap items-center gap-2 md:justify-start">
          <ExperimentSideSelect
            label="Left"
            value={leftExperimentId ?? ""}
            experiments={selectedExperiments}
            disabledExperimentId={rightExperimentId}
            onValueChange={onLeftChange}
          />
          <ParentExperimentMenu
            side="right"
            parentExperiment={leftParentExperiment}
            onChooseParent={onUseLeftParentAsRight}
          />
        </div>

        <div className="flex justify-center">
          <Tooltip>
            <TooltipTrigger asChild>
              <span className="shrink-0">
                <Button
                  type="button"
                  variant="outline"
                  size="icon"
                  className="h-8 w-8"
                  onClick={onSwap}
                  disabled={!rightExperimentId}
                  aria-label="Swap left and right experiments"
                >
                  <ArrowLeftRight className="h-4 w-4" />
                </Button>
              </span>
            </TooltipTrigger>
            <TooltipContent>Swap left and right experiments</TooltipContent>
          </Tooltip>
        </div>

        <div className="flex min-w-0 flex-wrap items-center gap-2 md:justify-end">
          <ExperimentSideSelect
            label="Right"
            value={rightExperimentId ?? NONE_VALUE}
            experiments={selectedExperiments}
            disabledExperimentId={leftExperimentId}
            includeNone
            onValueChange={onRightChange}
          />
          <ParentExperimentMenu
            side="left"
            parentExperiment={rightParentExperiment}
            onChooseParent={onUseRightParentAsLeft}
          />
        </div>
      </div>
    </TooltipProvider>
  );
}

function ParentExperimentMenu({
  side,
  parentExperiment,
  onChooseParent,
}: {
  side: "left" | "right";
  parentExperiment: Experiment | null;
  onChooseParent: (experimentId: string) => void;
}) {
  const hasParent = Boolean(parentExperiment);
  const tooltip =
    side === "right"
      ? hasParent
        ? "Choose parent in right"
        : "Left experiment has no parent"
      : hasParent
        ? "Choose parent in left"
        : "Right experiment has no parent";

  return (
    <DropdownMenu>
      <Tooltip>
        <TooltipTrigger asChild>
          <span className="shrink-0">
            <DropdownMenuTrigger asChild disabled={!hasParent}>
              <Button
                type="button"
                variant="outline"
                size="icon"
                className={cn(
                  "h-8 w-8",
                  !hasParent &&
                    "border-dashed border-amber-300 bg-amber-50 text-amber-700 opacity-100 disabled:opacity-100 dark:border-amber-900/70 dark:bg-amber-950/30 dark:text-amber-400"
                )}
                disabled={!hasParent}
                aria-label={tooltip}
              >
                <MoreHorizontal className="h-4 w-4" />
              </Button>
            </DropdownMenuTrigger>
          </span>
        </TooltipTrigger>
        <TooltipContent>{tooltip}</TooltipContent>
      </Tooltip>
      <DropdownMenuContent align={side === "right" ? "start" : "end"} className="w-64">
        {parentExperiment ? (
          <DropdownMenuItem onSelect={() => onChooseParent(parentExperiment.id)}>
            <GitBranch className="h-4 w-4" />
            <span className="min-w-0 truncate">
              Choose parent in {side}: {parentExperiment.name}
            </span>
          </DropdownMenuItem>
        ) : null}
      </DropdownMenuContent>
    </DropdownMenu>
  );
}

function ExperimentSideSelect({
  label,
  value,
  experiments,
  disabledExperimentId,
  includeNone = false,
  onValueChange,
}: {
  label: string;
  value: string;
  experiments: Experiment[];
  disabledExperimentId: string | null;
  includeNone?: boolean;
  onValueChange: (experimentId: string) => void;
}) {
  return (
    <label className="flex min-w-0 items-center gap-2 text-sm">
      <span className="shrink-0 text-muted-foreground">{label}</span>
      <Select value={value} onValueChange={onValueChange}>
        <SelectTrigger className="h-8 w-64">
          <SelectValue />
        </SelectTrigger>
        <SelectContent>
          {includeNone ? <SelectItem value={NONE_VALUE}>No comparison</SelectItem> : null}
          {experiments.map((experiment) => (
            <SelectItem
              key={experiment.id}
              value={experiment.id}
              disabled={experiment.id === disabledExperimentId}
            >
              <ExperimentOption experiment={experiment} />
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
    </label>
  );
}

function ExperimentOption({ experiment }: { experiment: Experiment }) {
  return (
    <span className="inline-flex min-w-0 items-center gap-2">
      <span
        className="h-2.5 w-2.5 shrink-0 rounded-full"
        style={{ backgroundColor: experiment.color || "#3b82f6" }}
      />
      <span className="min-w-0 truncate">{experiment.name}</span>
    </span>
  );
}

function CenteredState({
  children,
  className,
}: {
  children: React.ReactNode;
  className?: string;
}) {
  return (
    <div
      className={cn(
        "flex min-h-0 flex-1 items-center justify-center p-6 text-sm text-muted-foreground",
        className
      )}
    >
      {children}
    </div>
  );
}
