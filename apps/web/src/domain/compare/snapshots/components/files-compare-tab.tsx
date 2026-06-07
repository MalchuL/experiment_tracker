"use client";

import { useEffect, useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { ArrowLeftRight, Download, GitBranch, Loader2, MoreHorizontal } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
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
import { experimentSnapshotsService } from "@/domain/experiments/services";
import type { Experiment } from "@/domain/experiments/types";
import { downloadBlob } from "@/lib/downloads";
import { QUERY_KEYS } from "@/lib/constants/query-keys";
import { useToast } from "@/lib/hooks/use-toast";
import { cn } from "@/lib/utils";
import { snapshotCompareService } from "../services/snapshot-compare-service";
import type { ExperimentSnapshotFiles } from "../types/snapshot-compare";
import { FileCompareView } from "./file-compare-view";

interface FilesCompareTabProps {
  projectId: string;
  allExperiments: Experiment[];
  selectedExperiments: Experiment[];
  onEnsureExperimentSelected: (experimentId: string) => void;
}

const NONE_VALUE = "__none";
type SnapshotDownloadTarget = {
  experimentId: string;
  experimentName: string;
  snapshotId: string;
  side: "left" | "right";
} | null;

export function FilesCompareTab({
  projectId,
  allExperiments,
  selectedExperiments,
  onEnsureExperimentSelected,
}: FilesCompareTabProps) {
  const { toast } = useToast();
  const [leftExperimentId, setLeftExperimentId] = useState<string | null>(null);
  const [rightExperimentId, setRightExperimentId] = useState<string | null>(null);
  const [displayedLeft, setDisplayedLeft] = useState<ExperimentSnapshotFiles | null>(null);
  const [displayedRight, setDisplayedRight] = useState<ExperimentSnapshotFiles | null>(null);
  const [downloadTarget, setDownloadTarget] = useState<SnapshotDownloadTarget>(null);
  const [snapshotDownloadPending, setSnapshotDownloadPending] = useState(false);

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
    const effectiveLeftId =
      leftExperimentId && selectedIds.has(leftExperimentId)
        ? leftExperimentId
        : selectedExperiments[0]?.id ?? null;
    setLeftExperimentId(effectiveLeftId);
    setRightExperimentId((current) => {
      if (current && selectedIds.has(current) && current !== effectiveLeftId) {
        return current;
      }
      return selectedExperiments.find((experiment) => experiment.id !== effectiveLeftId)
        ?.id ?? null;
    });
  }, [leftExperimentId, selectedExperiments]);

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

  const leftQuery = useQuery({
    queryKey: [
      QUERY_KEYS.COMPARE.SNAPSHOT_FILES_BY_EXPERIMENT(leftExperimentId ?? undefined),
    ],
    queryFn: () => {
      if (!leftExperimentId) {
        throw new Error("Left experiment is not selected");
      }
      return snapshotCompareService.getExperimentSnapshotFiles(leftExperimentId);
    },
    enabled: Boolean(
      leftExperimentId && displayedLeft?.experimentId !== leftExperimentId
    ),
  });

  const rightQuery = useQuery({
    queryKey: [
      QUERY_KEYS.COMPARE.SNAPSHOT_FILES_BY_EXPERIMENT(rightExperimentId ?? undefined),
    ],
    queryFn: () => {
      if (!rightExperimentId) {
        throw new Error("Right experiment is not selected");
      }
      return snapshotCompareService.getExperimentSnapshotFiles(rightExperimentId);
    },
    enabled: Boolean(
      rightExperimentId && displayedRight?.experimentId !== rightExperimentId
    ),
  });

  const loadedLeft =
    leftQuery.data?.experimentId === leftExperimentId ? leftQuery.data : undefined;
  const loadedRight =
    rightExperimentId && rightQuery.data?.experimentId === rightExperimentId
      ? rightQuery.data
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

  if (!leftExperimentId) {
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

  if (leftQuery.isLoading && !displayedLeft) {
    return <CenteredState>Loading snapshots...</CenteredState>;
  }

  if (
    (leftQuery.isError && !displayedLeft) ||
    (rightQuery.isError && !displayedRight)
  ) {
    return <CenteredState>Failed to load snapshot files.</CenteredState>;
  }

  const left = loadedLeft ?? displayedLeft;
  const right = rightExperimentId ? loadedRight ?? displayedRight ?? undefined : undefined;
  const renderedLeftExperiment = left
    ? experimentsById.get(left.experimentId) ??
      selectedExperiments.find((experiment) => experiment.id === left.experimentId) ??
      null
    : leftExperiment;
  const renderedRightExperiment = right
    ? experimentsById.get(right.experimentId) ??
      selectedExperiments.find((experiment) => experiment.id === right.experimentId) ??
      null
    : rightExperiment;

  const controls = (
    <FilesCompareControls
      selectedExperiments={selectedExperiments}
      leftExperimentId={leftExperimentId}
      rightExperimentId={rightExperimentId}
      leftExperimentName={renderedLeftExperiment?.name ?? left?.experimentId ?? "Left"}
      rightExperimentName={renderedRightExperiment?.name ?? right?.experimentId ?? "Right"}
      leftSnapshotId={left?.snapshotId ?? null}
      rightSnapshotId={right?.snapshotId ?? null}
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
      onDownloadSnapshot={setDownloadTarget}
      onSwap={() => {
        if (!rightExperimentId) {
          return;
        }
        setLeftExperimentId(rightExperimentId);
        setRightExperimentId(leftExperimentId);
      }}
    />
  );

  const handleDownloadSnapshot = async () => {
    if (!downloadTarget) return;
    setSnapshotDownloadPending(true);
    try {
      const { blob, filename } = await experimentSnapshotsService.download(
        downloadTarget.experimentId,
        downloadTarget.snapshotId
      );
      downloadBlob(blob, filename);
      setDownloadTarget(null);
      toast({ title: "Snapshot download started" });
    } catch {
      toast({
        title: "Failed to download snapshot",
        description: "The selected snapshot could not be downloaded.",
        variant: "destructive",
      });
    } finally {
      setSnapshotDownloadPending(false);
    }
  };

  return (
    <div className="flex min-h-0 flex-1 flex-col">
      {controls}
      <FileCompareView
        projectId={projectId}
        leftFiles={left?.snapshotId ? left.files : []}
        rightFiles={rightExperimentId ? (right?.snapshotId ? right.files : []) : undefined}
        leftLabel={renderedLeftExperiment?.name ?? left?.experimentId ?? "Left"}
        rightLabel={renderedRightExperiment?.name ?? right?.experimentId ?? undefined}
        rightExperimentId={rightExperimentId ? right?.experimentId : undefined}
        leftSnapshotId={left?.snapshotId ?? undefined}
        rightSnapshotId={right?.snapshotId ?? undefined}
        leftSnapshotMissing={Boolean(
          left && left.experimentId === leftExperimentId && !left.snapshotId
        )}
        rightSnapshotMissing={Boolean(
          rightExperimentId &&
            right &&
            right.experimentId === rightExperimentId &&
            !right.snapshotId
        )}
      />
      <Dialog
        open={downloadTarget !== null}
        onOpenChange={(open) => {
          if (!open && !snapshotDownloadPending) setDownloadTarget(null);
        }}
      >
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Download snapshot?</DialogTitle>
            <DialogDescription>
              This will download the {downloadTarget?.side} snapshot for{" "}
              {downloadTarget?.experimentName ?? "this experiment"} as a ZIP archive.
            </DialogDescription>
          </DialogHeader>
          <div className="rounded-md bg-muted/40 p-3 text-xs text-muted-foreground">
            <div className="truncate font-medium text-foreground">{downloadTarget?.experimentName}</div>
            <div className="break-all">{downloadTarget?.snapshotId}</div>
          </div>
          <DialogFooter>
            <Button
              type="button"
              variant="outline"
              disabled={snapshotDownloadPending}
              onClick={() => setDownloadTarget(null)}
            >
              Cancel
            </Button>
            <Button
              type="button"
              disabled={snapshotDownloadPending}
              onClick={handleDownloadSnapshot}
            >
              {snapshotDownloadPending ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <Download className="h-4 w-4" />
              )}
              Download
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}

function FilesCompareControls({
  selectedExperiments,
  leftExperimentId,
  rightExperimentId,
  leftExperimentName,
  rightExperimentName,
  leftSnapshotId,
  rightSnapshotId,
  leftParentExperiment,
  rightParentExperiment,
  onLeftChange,
  onRightChange,
  onUseLeftParentAsRight,
  onUseRightParentAsLeft,
  onDownloadSnapshot,
  onSwap,
}: {
  selectedExperiments: Experiment[];
  leftExperimentId: string | null;
  rightExperimentId: string | null;
  leftExperimentName: string;
  rightExperimentName: string;
  leftSnapshotId: string | null;
  rightSnapshotId: string | null;
  leftParentExperiment: Experiment | null;
  rightParentExperiment: Experiment | null;
  onLeftChange: (experimentId: string) => void;
  onRightChange: (experimentId: string) => void;
  onUseLeftParentAsRight: (experimentId: string) => void;
  onUseRightParentAsLeft: (experimentId: string) => void;
  onDownloadSnapshot: (target: NonNullable<SnapshotDownloadTarget>) => void;
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
          <SideActionsMenu
            side="right"
            sourceSide="left"
            experimentId={leftExperimentId}
            experimentName={leftExperimentName}
            snapshotId={leftSnapshotId}
            parentExperiment={leftParentExperiment}
            onChooseParent={onUseLeftParentAsRight}
            onDownloadSnapshot={onDownloadSnapshot}
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
          <SideActionsMenu
            side="left"
            sourceSide="right"
            experimentId={rightExperimentId}
            experimentName={rightExperimentName}
            snapshotId={rightSnapshotId}
            parentExperiment={rightParentExperiment}
            onChooseParent={onUseRightParentAsLeft}
            onDownloadSnapshot={onDownloadSnapshot}
          />
        </div>
      </div>
    </TooltipProvider>
  );
}

function SideActionsMenu({
  side,
  sourceSide,
  experimentId,
  experimentName,
  snapshotId,
  parentExperiment,
  onChooseParent,
  onDownloadSnapshot,
}: {
  side: "left" | "right";
  sourceSide: "left" | "right";
  experimentId: string | null;
  experimentName: string;
  snapshotId: string | null;
  parentExperiment: Experiment | null;
  onChooseParent: (experimentId: string) => void;
  onDownloadSnapshot: (target: NonNullable<SnapshotDownloadTarget>) => void;
}) {
  const hasParent = Boolean(parentExperiment);
  const canDownload = Boolean(experimentId && snapshotId);
  const hasActions = hasParent || canDownload;
  const tooltip = hasActions
    ? `${sourceSide === "left" ? "Left" : "Right"} actions`
    : "No actions";

  return (
    <DropdownMenu>
      <Tooltip>
        <TooltipTrigger asChild>
          <span className="shrink-0">
            <DropdownMenuTrigger asChild disabled={!hasActions}>
              <Button
                type="button"
                variant="outline"
                size="icon"
                className={cn(
                  "h-8 w-8",
                  !hasActions &&
                    "border-dashed border-amber-300 bg-amber-50 text-amber-700 opacity-100 disabled:opacity-100 dark:border-amber-900/70 dark:bg-amber-950/30 dark:text-amber-400"
                )}
                disabled={!hasActions}
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
        {experimentId && snapshotId ? (
          <DropdownMenuItem
            onSelect={() =>
              onDownloadSnapshot({
                experimentId,
                experimentName,
                snapshotId,
                side: sourceSide,
              })
            }
          >
            <Download className="h-4 w-4" />
            <span className="min-w-0 truncate">Download snapshot</span>
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
