"use client";

import { useEffect, useMemo, useState, type ReactNode } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { ArrowLeftRight, ArrowRight, CircleMinus, CirclePlus, GitCompare, Maximize2, PencilLine, Save } from "lucide-react";
import type { Experiment } from "@/domain/experiments/types";
import { experimentsService } from "@/domain/experiments/services";
import { QUERY_KEYS } from "@/lib/constants/query-keys";
import { useToast } from "@/lib/hooks/use-toast";
import { cn } from "@/lib/utils";
import {
  diffFeatureTrees,
  parseFeatureNodes,
  type FeatureDiffNode,
  type FeatureNode,
} from "@/lib/features/feature-tree";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { FeatureBulletEditor } from "@/components/shared/feature-bullet-editor";
import { FeatureEditorLabelWithHelp } from "@/components/shared/feature-editor-help";

type ExperimentFeaturesPanelProps = {
  experiment: Experiment;
  parentExperiment?: Experiment;
  projectExperiments: Experiment[];
  experimentsLoading?: boolean;
  modalOpen: boolean;
  onModalOpenChange: (open: boolean) => void;
  lockExperimentFeaturesSelection?: boolean;
  showDiffs: boolean;
  onShowDiffsChange: (showDiffs: boolean) => void;
};

type FlatDiffLine = {
  key: string;
  depth: number;
  status: FeatureDiffNode["status"];
  parentName: string;
  childName: string;
};

const FEATURE_TREE_INDENT_PX = 22;
const FEATURE_TREE_TEXT_CLASS = "inline-block min-w-full font-sans text-xs";

export function ExperimentFeaturesPanel({
  experiment,
  parentExperiment,
  projectExperiments,
  experimentsLoading = false,
  modalOpen,
  onModalOpenChange,
  lockExperimentFeaturesSelection = false,
  showDiffs,
  onShowDiffsChange,
}: ExperimentFeaturesPanelProps) {
  const childFeatures = parseFeatureNodes(experiment.features);
  const parentFeatures = parseFeatureNodes(parentExperiment?.features);
  const diffRows = useMemo(
    () => diffFeatureTrees(parentExperiment ? parentFeatures : childFeatures, childFeatures),
    [parentExperiment, parentFeatures, childFeatures]
  );
  const summary = useMemo(() => summarizeDiff(diffRows), [diffRows]);
  const [expandedOpen, setExpandedOpen] = useState(false);

  return (
    <div className="w-full min-w-0 max-w-full overflow-hidden">
      <Card className="w-full min-w-0 max-w-full overflow-hidden">
        <CardHeader className="flex min-w-0 flex-row items-center justify-between gap-2 px-3 py-2">
          <CardTitle className="min-w-0 truncate text-xs font-medium text-muted-foreground">
            Features
          </CardTitle>
          <div className="flex shrink-0 items-center gap-2">
            <Button
              type="button"
              variant={showDiffs ? "default" : "outline"}
              size="icon"
              className="h-8 w-8"
              onClick={() => onShowDiffsChange(!showDiffs)}
              aria-pressed={showDiffs}
              aria-label={showDiffs ? "Disable feature diffs" : "Enable feature diffs"}
              title={showDiffs ? "Disable feature diffs" : "Enable feature diffs"}
            >
              <GitCompare className="h-3.5 w-3.5" />
            </Button>
            <Button
              type="button"
              variant="outline"
              size="icon"
              className="h-8 w-8 shrink-0"
              onClick={() => setExpandedOpen(true)}
              aria-label="Expand feature diff"
              title="Expand feature diff"
              data-testid="button-expand-feature-diff"
            >
              <Maximize2 className="h-3.5 w-3.5" />
            </Button>
            <Button
              type="button"
              variant="outline"
              size="icon"
              className="h-8 w-8 shrink-0"
              onClick={() => onModalOpenChange(true)}
              aria-label="Edit feature comparison"
              title="Edit feature comparison"
              data-testid="button-edit-feature-comparison"
            >
              <PencilLine className="h-3.5 w-3.5" />
            </Button>
          </div>
        </CardHeader>
        <CardContent className="w-full min-w-0 max-w-full space-y-2 overflow-hidden px-3 pb-3 pt-0">
          {parentExperiment && showDiffs ? (
            <div className="flex flex-wrap gap-1">
              <FeatureCountBadge label="Added" value={summary.added} className="border-green-500/20 bg-green-500/10 text-green-700" />
              <FeatureCountBadge label="Removed" value={summary.removed} className="border-red-500/20 bg-red-500/10 text-red-700" />
              <FeatureCountBadge label="Changed" value={summary.changed + summary.renamed} className="border-amber-500/20 bg-amber-500/10 text-amber-700" />
            </div>
          ) : null}
          <FeatureView
            childFeatures={childFeatures}
            parentExperimentExists={parentExperiment != null}
            diffRows={diffRows}
            showDiffs={showDiffs}
          />
        </CardContent>
      </Card>
      <FeatureExpandedModal
        open={expandedOpen}
        onOpenChange={setExpandedOpen}
        childFeatures={childFeatures}
        parentExperimentExists={parentExperiment != null}
        diffRows={diffRows}
        summary={summary}
        showDiffs={showDiffs}
        onShowDiffsChange={onShowDiffsChange}
      />
      <ExperimentFeaturesCompareModal
        open={modalOpen}
        onOpenChange={onModalOpenChange}
        currentExperiment={experiment}
        defaultParentExperiment={parentExperiment}
        projectExperiments={projectExperiments}
        experimentsLoading={experimentsLoading}
        lockExperimentFeaturesSelection={lockExperimentFeaturesSelection}
      />
    </div>
  );
}

function FeatureCountBadge({
  label,
  value,
  className,
}: {
  label: string;
  value: number;
  className?: string;
}) {
  return (
    <Badge variant="outline" className={cn("text-[11px]", className)}>
      {label} {value}
    </Badge>
  );
}

function FeatureView({
  childFeatures,
  parentExperimentExists,
  diffRows,
  showDiffs,
}: {
  childFeatures: FeatureNode[];
  parentExperimentExists: boolean;
  diffRows: FeatureDiffNode[];
  showDiffs: boolean;
}) {
  if (childFeatures.length === 0 && !parentExperimentExists) {
    return <p className="py-4 text-center text-sm text-muted-foreground">No features</p>;
  }

  return showDiffs ? <FeatureDiffTree rows={diffRows} /> : <FeaturePlainTree features={childFeatures} />;
}

function FeatureExpandedModal({
  open,
  onOpenChange,
  childFeatures,
  parentExperimentExists,
  diffRows,
  summary,
  showDiffs,
  onShowDiffsChange,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  childFeatures: FeatureNode[];
  parentExperimentExists: boolean;
  diffRows: FeatureDiffNode[];
  summary: ReturnType<typeof summarizeDiff>;
  showDiffs: boolean;
  onShowDiffsChange: (showDiffs: boolean) => void;
}) {
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="flex h-[min(60rem,calc(100dvh-1rem))] max-w-[min(64rem,calc(100vw-2rem))] flex-col gap-3 p-0">
        <DialogHeader className="border-b px-4 py-3">
          <div className="flex items-start justify-between gap-3">
            <div className="min-w-0">
              <DialogTitle>Features</DialogTitle>
              <DialogDescription>Expanded feature comparison for this experiment.</DialogDescription>
            </div>
            <Button
              type="button"
              variant={showDiffs ? "default" : "outline"}
              size="icon"
              className="mr-6 h-8 w-8 shrink-0"
              onClick={() => onShowDiffsChange(!showDiffs)}
              aria-pressed={showDiffs}
              aria-label={showDiffs ? "Disable feature diffs" : "Enable feature diffs"}
              title={showDiffs ? "Disable feature diffs" : "Enable feature diffs"}
            >
              <GitCompare className="h-3.5 w-3.5" />
            </Button>
          </div>
          {showDiffs ? (
            <div className="flex flex-wrap gap-1 pt-2">
              <FeatureCountBadge label="Added" value={summary.added} className="border-green-500/20 bg-green-500/10 text-green-700" />
              <FeatureCountBadge label="Removed" value={summary.removed} className="border-red-500/20 bg-red-500/10 text-red-700" />
              <FeatureCountBadge label="Changed" value={summary.changed + summary.renamed} className="border-amber-500/20 bg-amber-500/10 text-amber-700" />
            </div>
          ) : null}
        </DialogHeader>
        <div className="min-h-0 flex-1 overflow-auto px-4 pb-4">
          <FeatureView
            childFeatures={childFeatures}
            parentExperimentExists={parentExperimentExists}
            diffRows={diffRows}
            showDiffs={showDiffs}
          />
        </div>
      </DialogContent>
    </Dialog>
  );
}

function FeaturePlainTree({ features }: { features: FeatureNode[] }) {
  const rows = useMemo(() => flattenFeatureNodes(features), [features]);
  if (rows.length === 0) {
    return <p className="py-4 text-center text-sm text-muted-foreground">No features</p>;
  }

  return (
    <div className="w-full min-w-0 max-w-full overflow-x-auto rounded border border-border [contain:inline-size]">
      <div className={FEATURE_TREE_TEXT_CLASS}>
        {rows.map((row) => (
          <FeatureUnifiedLine
            key={row.key}
            name={row.name}
            depth={row.depth}
            className="text-foreground/80"
          />
        ))}
      </div>
    </div>
  );
}

function FeatureDiffTree({ rows }: { rows: FeatureDiffNode[] }) {
  const flatRows = useMemo(() => flattenDiffRows(rows), [rows]);
  if (flatRows.length === 0) {
    return <p className="py-4 text-center text-sm text-muted-foreground">No features</p>;
  }

  return (
    <div className="w-full min-w-0 max-w-full overflow-x-auto rounded border border-border [contain:inline-size]">
      <div className={FEATURE_TREE_TEXT_CLASS}>
        {flatRows.map((row) => (
          <FeatureChangeRow key={row.key} row={row} />
        ))}
      </div>
    </div>
  );
}

function flattenFeatureNodes(
  features: FeatureNode[],
  depth = 0,
  prefix = "feature"
): Array<{ key: string; name: string; depth: number }> {
  return features.flatMap((feature, index) => [
    {
      key: `${prefix}:${index}:${feature.name}`,
      name: feature.name,
      depth,
    },
    ...flattenFeatureNodes(feature.children ?? [], depth + 1, `${prefix}:${index}`),
  ]);
}

function FeatureChangeRow({ row }: { row: FlatDiffLine }) {
  if (row.status === "unchanged") {
    return (
      <FeatureUnifiedLine
        name={row.childName || row.parentName}
        depth={row.depth}
        className="text-foreground/80"
      />
    );
  }

  const displayName = row.childName || row.parentName;
  const diffTitle = getFeatureDiffTitle(row);

  if ((row.status === "renamed" || row.status === "changed") && row.parentName && row.childName) {
    return (
      <FeatureChangedLine
        icon={<FeatureDiffIcon status={row.status} title={diffTitle} />}
        previousName={row.parentName}
        name={row.childName}
        depth={row.depth}
      />
    );
  }

  return (
    <FeatureUnifiedLine
      icon={<FeatureDiffIcon status={row.status} title={diffTitle} />}
      name={displayName}
      depth={row.depth}
      className={cn(
        row.status === "added" && "bg-green-500/10 text-green-800 dark:text-green-300",
        row.status === "removed" && "bg-red-500/10 text-red-800 dark:text-red-300",
        (row.status === "renamed" || row.status === "changed") &&
          "bg-amber-500/10 text-amber-800 dark:text-amber-300"
      )}
    />
  );
}

function FeatureUnifiedLine({
  icon,
  name,
  depth,
  className,
}: {
  icon?: ReactNode;
  name: string;
  depth: number;
  className?: string;
}) {
  return (
    <div className={cn("flex w-max min-w-full border-b border-border/35 px-2 py-1 last:border-b-0", className)}>
      <span className="flex w-4 shrink-0 select-none items-center justify-center">
        {icon}
      </span>
      <span className="inline-flex shrink-0 items-center whitespace-nowrap" style={{ paddingLeft: depth * FEATURE_TREE_INDENT_PX }}>
        <FeatureNodeDot />
        {name || " "}
      </span>
    </div>
  );
}

function FeatureChangedLine({
  icon,
  previousName,
  name,
  depth,
}: {
  icon?: ReactNode;
  previousName: string;
  name: string;
  depth: number;
}) {
  return (
    <div className="flex w-max min-w-full border-b border-border/25 bg-amber-500/10 px-2 py-1 text-amber-800 last:border-b-0 dark:text-amber-300">
      <span className="flex w-4 shrink-0 select-none items-start justify-center pt-0.5">
        {icon}
      </span>
      <span className="flex shrink-0 flex-col whitespace-nowrap" style={{ paddingLeft: depth * FEATURE_TREE_INDENT_PX }}>
        <span className="inline-flex items-center pl-2.5 text-muted-foreground line-through">
          {previousName || " "}
        </span>
        <span className="inline-flex items-center">
          <FeatureNodeDot />
          {name || " "}
        </span>
      </span>
    </div>
  );
}

function FeatureNodeDot() {
  return <span className="mr-1.5 h-1 w-1 shrink-0 rounded-full bg-muted-foreground/50" aria-hidden="true" />;
}

function FeatureDiffIcon({
  status,
  title,
}: {
  status: FeatureDiffNode["status"];
  title: string;
}) {
  const iconClassName = "h-3.5 w-3.5";
  let icon: ReactNode = null;
  if (status === "added") {
    icon = <CirclePlus className={cn(iconClassName, "text-green-700 dark:text-green-300")} />;
  } else if (status === "removed") {
    icon = <CircleMinus className={cn(iconClassName, "text-red-700 dark:text-red-300")} />;
  } else if (status === "renamed" || status === "changed") {
    icon = <PencilLine className={cn(iconClassName, "text-amber-700 dark:text-amber-300")} />;
  }

  return icon ? (
    <span title={title} aria-label={title} role="img">
      {icon}
    </span>
  ) : null;
}

function getFeatureDiffTitle(row: FlatDiffLine): string {
  if (row.status === "added") {
    return `${row.childName} was added in experiment and is not present in parent`;
  }
  if (row.status === "removed") {
    return `${row.parentName} was removed in experiment but is present in parent`;
  }
  if (row.status === "renamed") {
    return `${row.parentName} was changed to ${row.childName} in experiment`;
  }
  if (row.status === "changed") {
    return `${row.childName || row.parentName} was changed in experiment`;
  }
  return `${row.childName || row.parentName} is unchanged`;
}

function ExperimentFeaturesCompareModal({
  open,
  onOpenChange,
  currentExperiment,
  defaultParentExperiment,
  projectExperiments,
  experimentsLoading,
  lockExperimentFeaturesSelection,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  currentExperiment: Experiment;
  defaultParentExperiment?: Experiment;
  projectExperiments: Experiment[];
  experimentsLoading: boolean;
  lockExperimentFeaturesSelection: boolean;
}) {
  const { toast } = useToast();
  const queryClient = useQueryClient();
  const [parentExperimentId, setParentExperimentId] = useState(defaultParentExperiment?.id ?? "");
  const [childExperimentId, setChildExperimentId] = useState(currentExperiment.id);
  const [swapped, setSwapped] = useState(false);
  const [childDraftFeatures, setChildDraftFeatures] = useState<FeatureNode[]>(
    parseFeatureNodes(currentExperiment.features)
  );
  const [error, setError] = useState<string | null>(null);

  const parentExperiment = projectExperiments.find((exp) => exp.id === parentExperimentId) ?? defaultParentExperiment;
  const childExperiment = projectExperiments.find((exp) => exp.id === childExperimentId) ?? currentExperiment;
  const parentFeatures = parseFeatureNodes(parentExperiment?.features);
  const childFeatures = parseFeatureNodes(childExperiment.features);
  const effectiveSwapped = lockExperimentFeaturesSelection ? false : swapped;

  useEffect(() => {
    if (!open) return;
    setParentExperimentId(defaultParentExperiment?.id ?? "");
    setChildExperimentId(currentExperiment.id);
    setSwapped(false);
    setChildDraftFeatures(parseFeatureNodes(currentExperiment.features));
    setError(null);
  }, [open, currentExperiment, defaultParentExperiment]);

  useEffect(() => {
    if (!open) return;
    setChildDraftFeatures(childFeatures);
    setError(null);
  }, [open, childExperimentId]);

  const updateFeaturesMutation = useMutation({
    mutationFn: ({ experimentId, features }: { experimentId: string; features: FeatureNode[] }) =>
      experimentsService.update(experimentId, { features }),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: [QUERY_KEYS.EXPERIMENTS.BY_ID(variables.experimentId)] });
      queryClient.invalidateQueries({ queryKey: [QUERY_KEYS.EXPERIMENTS.BY_PROJECT(currentExperiment.projectId)] });
    },
  });

  const leftLabel = effectiveSwapped ? childExperiment.name : parentExperiment?.name ?? "No comparison experiment";
  const rightLabel = effectiveSwapped ? parentExperiment?.name ?? "No comparison experiment" : childExperiment.name;
  const compareBaseFeatures = effectiveSwapped ? childDraftFeatures : parentFeatures;
  const compareExperimentFeatures = effectiveSwapped ? parentFeatures : childDraftFeatures;

  const saveExperimentFeatures = async () => {
    const normalizedFeatures = normalizeEditedFeatures(childDraftFeatures);
    if (featureTreeHasBlankName(normalizedFeatures)) {
      setError("Feature names cannot be empty.");
      return;
    }
    setError(null);
    await updateFeaturesMutation.mutateAsync({ experimentId: childExperiment.id, features: normalizedFeatures });
    toast({ title: "Features updated", description: "Experiment features have been saved." });
    onOpenChange(false);
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="flex h-[min(48rem,calc(100dvh-2rem))] max-w-[min(72rem,calc(100vw-2rem))] flex-col gap-3 p-0">
        <DialogHeader className="px-4 pt-4">
          <DialogTitle>Compare features</DialogTitle>
          <DialogDescription>
            Select experiments to compare. Edit experiment features as an indented outline.
          </DialogDescription>
        </DialogHeader>
        <div className="grid gap-2 px-4 md:grid-cols-[1fr_auto_1fr]">
          <div className={cn(effectiveSwapped ? "md:order-1" : "md:order-3")}>
            <ExperimentSelect
              label="Compare with"
              value={parentExperimentId || "__none__"}
              experiments={projectExperiments}
              loading={experimentsLoading}
              onChange={(value) => setParentExperimentId(value === "__none__" ? "" : value)}
              includeNone
            />
          </div>
          {lockExperimentFeaturesSelection ? (
            <div className="flex h-10 items-center justify-center self-end text-muted-foreground md:order-2" aria-hidden="true">
              <ArrowRight className="h-4 w-4" />
            </div>
          ) : (
            <Button
              type="button"
              variant="outline"
              size="icon"
              className="self-end md:order-2"
              onClick={() => setSwapped((value) => !value)}
              aria-label="Switch compare sides"
            >
              <ArrowLeftRight className="h-4 w-4" />
            </Button>
          )}
          <div className={cn(effectiveSwapped ? "md:order-3" : "md:order-1")}>
            <ExperimentSelect
              label="Experiment features"
              value={childExperimentId}
              experiments={projectExperiments.length ? projectExperiments : [currentExperiment]}
              loading={experimentsLoading}
              onChange={setChildExperimentId}
              disabled={lockExperimentFeaturesSelection}
            />
          </div>
        </div>
        <div className="grid min-h-0 flex-1 grid-rows-[minmax(0,1fr)_minmax(0,1fr)] gap-3 px-4 pb-4 lg:grid-cols-2 lg:grid-rows-1">
          <div className="flex min-h-0 overflow-hidden flex-col gap-2">
            <FeatureEditorLabelWithHelp
              label="Experiment features"
              className="text-xs font-medium text-muted-foreground"
            />
            <FeatureBulletEditor
              key={childExperimentId}
              features={childDraftFeatures}
              onChange={setChildDraftFeatures}
              wrapperClassName="min-h-0 flex-1 overflow-auto rounded border border-input bg-background"
              className="min-h-full px-3 py-2 text-sm focus-visible:outline-none [&_ul]:list-disc [&_ul]:pl-5 [&_li]:my-1 [&_p]:m-0"
            />
            {error ? <p className="text-xs text-destructive">{error}</p> : null}
          </div>
          <FeatureStructuredDiff
            baseFeatures={compareBaseFeatures}
            experimentFeatures={compareExperimentFeatures}
            baseLabel={leftLabel}
            experimentLabel={rightLabel}
          />
        </div>
        <DialogFooter className="border-t px-4 py-3">
          <Button type="button" variant="outline" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <Button type="button" onClick={saveExperimentFeatures} disabled={updateFeaturesMutation.isPending} className="gap-1">
            <Save className="h-4 w-4" />
            {updateFeaturesMutation.isPending ? "Saving..." : "Save features"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

function ExperimentSelect({
  label,
  value,
  experiments,
  loading,
  onChange,
  includeNone = false,
  disabled = false,
}: {
  label: string;
  value: string;
  experiments: Experiment[];
  loading: boolean;
  onChange: (value: string) => void;
  includeNone?: boolean;
  disabled?: boolean;
}) {
  return (
    <label className="space-y-1">
      <span className="text-xs font-medium text-muted-foreground">{label}</span>
      <Select value={value} onValueChange={onChange} disabled={loading || disabled}>
        <SelectTrigger>
          <SelectValue />
        </SelectTrigger>
        <SelectContent>
          {includeNone ? <SelectItem value="__none__">No comparison experiment</SelectItem> : null}
          {experiments.map((experiment) => (
            <SelectItem key={experiment.id} value={experiment.id}>
              {experiment.name} ({experiment.id.slice(0, 7)})
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
    </label>
  );
}

function FeatureStructuredDiff({
  baseFeatures,
  experimentFeatures,
  baseLabel,
  experimentLabel,
}: {
  baseFeatures: FeatureNode[];
  experimentFeatures: FeatureNode[];
  baseLabel: string;
  experimentLabel: string;
}) {
  const rows = useMemo(
    () => diffFeatureTrees(baseFeatures, experimentFeatures),
    [baseFeatures, experimentFeatures]
  );
  const summary = useMemo(() => summarizeDiff(rows), [rows]);

  return (
    <div className="flex min-h-0 flex-col overflow-hidden rounded border border-border">
      <div className="flex items-center justify-between gap-3 border-b bg-muted/30 px-3 py-2 text-xs">
        <div className="min-w-0 truncate">
          <span className="font-medium">Comparing:</span>{" "}
          <span className="text-muted-foreground">{baseLabel}</span>
          <span className="text-muted-foreground"> ↔ </span>
          <span className="text-muted-foreground">{experimentLabel}</span>
        </div>
        <div className="flex gap-1">
          <Badge variant="outline" className="border-green-500/20 bg-green-500/10 text-green-700">+{summary.added}</Badge>
          <Badge variant="outline" className="border-red-500/20 bg-red-500/10 text-red-700">-{summary.removed}</Badge>
          <Badge variant="outline" className="border-amber-500/20 bg-amber-500/10 text-amber-700">
            ~{summary.changed + summary.renamed}
          </Badge>
        </div>
      </div>
      <div className="min-h-0 flex-1 overflow-auto p-2">
        <FeatureDiffTree rows={rows} />
      </div>
    </div>
  );
}

function flattenDiffRows(rows: FeatureDiffNode[], depth = 0): FlatDiffLine[] {
  return rows.flatMap((row) => [
    {
      key: row.key,
      depth,
      status: row.status,
      parentName: row.parent?.name ?? "",
      childName: row.child?.name ?? "",
    },
    ...flattenDiffRows(row.children, depth + 1),
  ]);
}

function summarizeDiff(rows: FeatureDiffNode[]) {
  const summary = { added: 0, removed: 0, renamed: 0, changed: 0 };
  for (const row of flattenDiffRows(rows)) {
    if (row.status === "added") summary.added += 1;
    if (row.status === "removed") summary.removed += 1;
    if (row.status === "renamed") summary.renamed += 1;
    if (row.status === "changed") summary.changed += 1;
  }
  return summary;
}

function normalizeEditedFeatures(features: FeatureNode[]): FeatureNode[] {
  return features.map((feature) => ({
    name: feature.name.trim(),
    ...(feature.children?.length
      ? { children: normalizeEditedFeatures(feature.children) }
      : {}),
  }));
}

function featureTreeHasBlankName(features: FeatureNode[]): boolean {
  return features.some(
    (feature) =>
      feature.name.trim() === "" ||
      (feature.children != null && featureTreeHasBlankName(feature.children))
  );
}
