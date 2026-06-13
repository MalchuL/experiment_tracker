"use client";

import { useEffect, useMemo, useState, type Dispatch, type ReactNode, type SetStateAction } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import * as AccordionPrimitive from "@radix-ui/react-accordion";
import { ChevronDown, GitCompare, Maximize2, PencilLine, Plus, X } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  Accordion,
  AccordionContent,
  AccordionItem,
} from "@/components/ui/accordion";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import {
  LoggedMetricAddDialog,
  type LoggedMetricAddDialogMode,
} from "@/components/shared/logged-metric-add-dialog";
import {
  MetricNameValueDiffRow,
} from "@/components/shared/metric-name-value-diff-row";
import type { Metric } from "@/domain/metrics/types";
import type { ProjectMetric } from "@/domain/projects/types";
import { metricsService } from "@/domain/metrics/services/metrics-service";
import { QUERY_KEYS } from "@/lib/constants/query-keys";
import { displayMetricKeyEquals } from "@/lib/metrics/format-metric-label";
import { parseLoggedMetricValueInput } from "@/lib/metrics/logged-metric-value-input";
import {
  formatMetricScalarForEditorDraft,
  formatMetricScalarForEditorFull,
  formatMetricScalarForDisplay,
  metricEditorValuesEffectivelyEqual,
} from "@/lib/metrics/metric-value-display";
import { useToast } from "@/lib/hooks/use-toast";
import { cn } from "@/lib/utils";

import {
  METRIC_SIDEBAR_DENSE_CLASS_NAMES,
  METRIC_SIDEBAR_ROW_REMOVE_BUTTON_CLASS,
  METRIC_SIDEBAR_ROW_REMOVE_CELL_CLASS,
  METRIC_SIDEBAR_ROW_REMOVE_ICON_CLASS,
  METRIC_SIDEBAR_UNTRACKED_CLASS_NAMES,
  METRIC_SIDEBAR_VALUE_DISPLAY_CLASS,
  METRIC_SIDEBAR_VALUE_INPUT_CLASS,
  loggedMetricRowGroupTableClass,
} from "@/components/shared/experiment-sidebar-metric-styles";

type LoggedMetricsLabelGroup = { label: string | null; items: Metric[] };

function accordionItemValueForLoggedLabelGroup(label: string | null): string {
  if (label == null || label === "") return "__unlabeled__";
  return label;
}

const LOGGED_METRICS_COLLAPSED_STORAGE_KEY = "experiment-sidebar.logged-metrics-collapsed";

function loggedMetricsCollapsedStorageKey(projectId: string): string {
  return `${LOGGED_METRICS_COLLAPSED_STORAGE_KEY}.${projectId}`;
}

function readStoredCollapsedLoggedMetricGroups(projectId: string): string[] {
  if (typeof window === "undefined") return [];
  try {
    const raw = window.localStorage.getItem(loggedMetricsCollapsedStorageKey(projectId));
    if (!raw) return [];
    const parsed = JSON.parse(raw) as unknown;
    return Array.isArray(parsed) ? parsed.filter((key): key is string => typeof key === "string") : [];
  } catch {
    return [];
  }
}

function writeStoredCollapsedLoggedMetricGroups(projectId: string, collapsedKeys: string[]) {
  if (typeof window === "undefined") return;
  try {
    const key = loggedMetricsCollapsedStorageKey(projectId);
    if (collapsedKeys.length === 0) {
      window.localStorage.removeItem(key);
    } else {
      window.localStorage.setItem(key, JSON.stringify(collapsedKeys));
    }
  } catch {
    /* ignore quota / private mode */
  }
}

const LOGGED_METRICS_DIFFS_STORAGE_KEY = "experiment-sidebar.logged-metrics-diffs";

function readStoredLoggedMetricDiffsEnabled(fallback: boolean): boolean {
  if (typeof window === "undefined") return fallback;
  try {
    const storedValue = window.localStorage.getItem(LOGGED_METRICS_DIFFS_STORAGE_KEY);
    if (storedValue === "1") return true;
    if (storedValue === "0") return false;
    return fallback;
  } catch {
    return fallback;
  }
}

function writeStoredLoggedMetricDiffsEnabled(enabled: boolean) {
  if (typeof window === "undefined") return;
  try {
    window.localStorage.setItem(LOGGED_METRICS_DIFFS_STORAGE_KEY, enabled ? "1" : "0");
  } catch {
    /* ignore quota / private mode */
  }
}

function lookupLoggedMetricValue(
  metrics: Metric[] | undefined,
  name: string,
  label: string | null
): number | null | undefined {
  const matchedRow = metrics?.find((row) =>
    displayMetricKeyEquals(
      { name: row.name, label: row.label ?? null },
      { name, label }
    )
  );
  return matchedRow?.value;
}

function findTrackedDefinitionForLoggedMetric(
  trackedDefinitions: ProjectMetric[],
  loggedMetric: Pick<Metric, "name" | "label">
): ProjectMetric | undefined {
  return trackedDefinitions.find((tracked) =>
    displayMetricKeyEquals(
      { name: loggedMetric.name, label: loggedMetric.label },
      { name: tracked.name, label: tracked.label ?? null }
    )
  );
}

function groupLoggedMetricsByLabel(metrics: Metric[] | undefined): LoggedMetricsLabelGroup[] {
  if (!metrics?.length) {
    return [];
  }
  const metricsByLabelKey = new Map<string, Metric[]>();
  for (const loggedMetric of metrics) {
    const rawLabelKey = loggedMetric.label ?? "";
    if (!metricsByLabelKey.has(rawLabelKey)) metricsByLabelKey.set(rawLabelKey, []);
    metricsByLabelKey.get(rawLabelKey)!.push(loggedMetric);
  }
  const sortedLabelEntries = [...metricsByLabelKey.entries()];
  sortedLabelEntries.sort((a, b) => {
    if (a[0] === "" && b[0] !== "") return 1;
    if (b[0] === "" && a[0] !== "") return -1;
    return a[0].localeCompare(b[0]);
  });
  for (const [, itemsInLabel] of sortedLabelEntries) {
    itemsInLabel.sort((a, b) => a.name.localeCompare(b.name));
  }
  return sortedLabelEntries.map(([rawLabelKey, itemsInLabel]) => ({
    label: rawLabelKey === "" ? null : rawLabelKey,
    items: itemsInLabel,
  }));
}

function SidebarEditableMetricValue({
  metric,
  draftValues,
  setDraftValues,
  onFlush,
}: {
  metric: Metric;
  draftValues: Record<string, string>;
  setDraftValues: Dispatch<SetStateAction<Record<string, string>>>;
  onFlush: (metric: Metric) => void | Promise<void>;
}) {
  const [editing, setEditing] = useState(false);
  const shortDraft = formatMetricScalarForEditorDraft(metric.value);

  if (!editing) {
    return (
      <button
        type="button"
        className={cn(
          METRIC_SIDEBAR_VALUE_DISPLAY_CLASS,
          "cursor-pointer rounded-sm outline-offset-1 hover:ring-1 hover:ring-border"
        )}
        title="Click to edit value"
        onClick={() => setEditing(true)}
        data-testid={`sidebar-metric-value-trigger-${metric.id}`}
      >
        {formatMetricScalarForDisplay(metric.value)}
      </button>
    );
  }

  return (
    <Input
      className={METRIC_SIDEBAR_VALUE_INPUT_CLASS}
      value={draftValues[metric.id] ?? shortDraft}
      autoFocus
      onChange={(event) =>
        setDraftValues((prev) => ({ ...prev, [metric.id]: event.target.value }))
      }
      onFocus={() =>
        setDraftValues((prev) => {
          const full = formatMetricScalarForEditorFull(metric.value);
          const cur = prev[metric.id] ?? shortDraft;
          const parsed = parseLoggedMetricValueInput(cur.trim());
          if (parsed === null) return prev;
          const stillServerValue =
            cur === shortDraft || metricEditorValuesEffectivelyEqual(parsed, metric.value);
          if (!stillServerValue || cur === full) return prev;
          return { ...prev, [metric.id]: full };
        })
      }
      onBlur={() => {
        void onFlush(metric);
        setEditing(false);
      }}
      onKeyDown={(event) => {
        if (event.key === "Enter") {
          event.currentTarget.blur();
        }
        if (event.key === "Escape") {
          setDraftValues((prev) => ({ ...prev, [metric.id]: shortDraft }));
          setEditing(false);
        }
      }}
      data-testid={`sidebar-metric-value-input-${metric.id}`}
    />
  );
}

type LoggedMetricsListProps = {
  loggedMetricsByLabel: LoggedMetricsLabelGroup[];
  openAccordionKeys: string[];
  onOpenAccordionKeysChange: (nextOpen: string[]) => void;
  hasParentLoggedMetrics: boolean;
  editMode: boolean;
  renderLoggedMetricRow: (loggedMetric: Metric) => ReactNode;
  onAddToGroup: (groupLabel: string | null) => void;
};

function LoggedMetricsList({
  loggedMetricsByLabel,
  openAccordionKeys,
  onOpenAccordionKeysChange,
  hasParentLoggedMetrics,
  editMode,
  renderLoggedMetricRow,
  onAddToGroup,
}: LoggedMetricsListProps) {
  if (loggedMetricsByLabel.length === 0) {
    return <p className="py-2 text-center text-sm text-muted-foreground">No metrics logged yet</p>;
  }

  return (
    <Accordion
      type="multiple"
      className="w-full"
      value={openAccordionKeys}
      onValueChange={onOpenAccordionKeysChange}
    >
      {loggedMetricsByLabel.map((labelGroup) => {
        const accordionItemValue = accordionItemValueForLoggedLabelGroup(labelGroup.label);
        const groupTitle =
          labelGroup.label != null && labelGroup.label !== "" ? labelGroup.label : "Unlabeled";

        return (
          <AccordionItem
            key={accordionItemValue}
            value={accordionItemValue}
            className="border-border last:border-b-0"
          >
            <AccordionPrimitive.Header className="flex items-center gap-1">
              <AccordionPrimitive.Trigger
                className={cn(
                  "flex flex-1 items-center justify-between gap-2 py-2 text-xs font-medium text-muted-foreground transition-all hover:no-underline [&[data-state=open]>svg]:rotate-180"
                )}
              >
                <span className="min-w-0 flex-1 truncate text-left">{groupTitle}</span>
                <ChevronDown className="h-4 w-4 shrink-0 transition-transform duration-200" />
              </AccordionPrimitive.Trigger>
              <Button
                type="button"
                variant="ghost"
                size="icon"
                className="h-4 w-4 shrink-0 text-muted-foreground hover:text-foreground"
                aria-label={
                  labelGroup.label != null
                    ? `Add metric under label ${labelGroup.label}`
                    : "Add unlabeled metric"
                }
                title={
                  labelGroup.label != null
                    ? `Add metric under ${labelGroup.label}`
                    : "Add unlabeled metric"
                }
                data-testid={`button-add-metric-group-${labelGroup.label ?? "unlabeled"}`}
                onClick={() => onAddToGroup(labelGroup.label)}
              >
                <Plus className="h-4 w-4" />
              </Button>
            </AccordionPrimitive.Header>
            <AccordionContent className="pb-2 pt-0">
              <div className={loggedMetricRowGroupTableClass(hasParentLoggedMetrics, editMode)}>
                {labelGroup.items.map((loggedMetric) => renderLoggedMetricRow(loggedMetric))}
              </div>
            </AccordionContent>
          </AccordionItem>
        );
      })}
    </Accordion>
  );
}

type LoggedMetricsHeaderActionsProps = {
  hasParentLoggedMetrics: boolean;
  showLoggedMetricDiffs: boolean;
  onToggleDiffs: () => void;
  onAddNewLabel: () => void;
  editMode: boolean;
  onToggleEditMode: () => void;
  includeExpand?: boolean;
  onExpand?: () => void;
  expandTestId?: string;
  headerActionsClassName?: string;
};

function LoggedMetricsHeaderActions({
  hasParentLoggedMetrics,
  showLoggedMetricDiffs,
  onToggleDiffs,
  onAddNewLabel,
  editMode,
  onToggleEditMode,
  includeExpand = false,
  onExpand,
  expandTestId = "button-expand-logged-metrics",
  headerActionsClassName,
}: LoggedMetricsHeaderActionsProps) {
  return (
    <div className={cn("flex shrink-0 items-center gap-2", headerActionsClassName)}>
      {hasParentLoggedMetrics ? (
        <Button
          type="button"
          variant={showLoggedMetricDiffs ? "default" : "outline"}
          size="icon"
          className="h-8 w-8 shrink-0"
          onClick={onToggleDiffs}
          aria-pressed={showLoggedMetricDiffs}
          aria-label={
            showLoggedMetricDiffs
              ? "Hide diffs for non-tracked metrics"
              : "Show diffs for non-tracked metrics"
          }
          title={
            showLoggedMetricDiffs
              ? "Hide diffs for non-tracked metrics"
              : "Show diffs for non-tracked metrics"
          }
          data-testid="button-logged-metrics-diffs"
        >
          <GitCompare className="h-3.5 w-3.5" />
        </Button>
      ) : null}
      {includeExpand && onExpand ? (
        <Button
          type="button"
          variant="outline"
          size="icon"
          className="h-8 w-8 shrink-0"
          onClick={onExpand}
          aria-label="Expand logged metrics"
          title="Expand logged metrics"
          data-testid={expandTestId}
        >
          <Maximize2 className="h-3.5 w-3.5" />
        </Button>
      ) : null}
      <Button
        type="button"
        size="icon"
        variant="outline"
        className="h-8 w-8 shrink-0"
        onClick={onAddNewLabel}
        data-testid="button-add-metric-label"
        aria-label="Add label & metric"
        title="Add label & metric"
      >
        <Plus className="h-3.5 w-3.5" />
      </Button>
      <Button
        type="button"
        variant={editMode ? "default" : "outline"}
        size="icon"
        className="h-8 w-8 shrink-0"
        onClick={onToggleEditMode}
        aria-pressed={editMode}
        aria-label={editMode ? "Stop editing existing metrics" : "Edit existing metrics"}
        title={editMode ? "Stop editing existing metrics" : "Edit existing metrics"}
        data-testid="switch-sidebar-logged-metrics-edit-mode"
      >
        <PencilLine className="h-3.5 w-3.5" />
      </Button>
    </div>
  );
}

function LoggedMetricsExpandedModal({
  open,
  onOpenChange,
  loggedMetricsByLabel,
  openAccordionKeys,
  onOpenAccordionKeysChange,
  hasParentLoggedMetrics,
  editMode,
  renderLoggedMetricRow,
  onAddToGroup,
  showLoggedMetricDiffs,
  onToggleDiffs,
  onAddNewLabel,
  onToggleEditMode,
}: LoggedMetricsListProps &
  Pick<
    LoggedMetricsHeaderActionsProps,
    | "hasParentLoggedMetrics"
    | "showLoggedMetricDiffs"
    | "onToggleDiffs"
    | "onAddNewLabel"
    | "editMode"
    | "onToggleEditMode"
  > & {
    open: boolean;
    onOpenChange: (open: boolean) => void;
  }) {
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="flex h-[min(60rem,calc(100dvh-1rem))] max-w-[min(64rem,calc(100vw-2rem))] flex-col gap-3 p-0">
        <DialogHeader className="border-b px-4 py-3">
          <div className="flex items-start justify-between gap-3">
            <div className="min-w-0">
              <DialogTitle>Logged Metrics</DialogTitle>
              <DialogDescription>Expanded logged metrics for this experiment.</DialogDescription>
            </div>
            <LoggedMetricsHeaderActions
              hasParentLoggedMetrics={hasParentLoggedMetrics}
              showLoggedMetricDiffs={showLoggedMetricDiffs}
              onToggleDiffs={onToggleDiffs}
              onAddNewLabel={onAddNewLabel}
              editMode={editMode}
              onToggleEditMode={onToggleEditMode}
              headerActionsClassName="mr-6"
            />
          </div>
        </DialogHeader>
        <div className="min-h-0 flex-1 overflow-auto px-4 pb-4">
          <LoggedMetricsList
            loggedMetricsByLabel={loggedMetricsByLabel}
            openAccordionKeys={openAccordionKeys}
            onOpenAccordionKeysChange={onOpenAccordionKeysChange}
            hasParentLoggedMetrics={hasParentLoggedMetrics}
            editMode={editMode}
            renderLoggedMetricRow={renderLoggedMetricRow}
            onAddToGroup={onAddToGroup}
          />
        </div>
      </DialogContent>
    </Dialog>
  );
}

export function ExperimentSidebarLoggedMetrics({
  experimentId,
  projectId,
  metrics,
  metricsLoading,
  parentLoggedMetrics,
  trackedMetricDefinitions,
}: {
  experimentId: string;
  projectId: string;
  metrics: Metric[] | undefined;
  metricsLoading: boolean;
  parentLoggedMetrics: Metric[] | undefined;
  trackedMetricDefinitions: ProjectMetric[];
}) {
  const { toast } = useToast();
  const queryClient = useQueryClient();
  const [editMode, setEditMode] = useState(false);
  const [draftValues, setDraftValues] = useState<Record<string, string>>({});
  const [addOpen, setAddOpen] = useState(false);
  const [addMode, setAddMode] = useState<LoggedMetricAddDialogMode>("group");
  const [addGroupLabel, setAddGroupLabel] = useState<string | null>(null);
  const [newName, setNewName] = useState("");
  const [newLabel, setNewLabel] = useState("");
  const [newValue, setNewValue] = useState("0");
  const [showLoggedMetricDiffs, setShowLoggedMetricDiffs] = useState(() =>
    readStoredLoggedMetricDiffsEnabled(true)
  );
  const [expandedOpen, setExpandedOpen] = useState(false);

  useEffect(() => {
    writeStoredLoggedMetricDiffsEnabled(showLoggedMetricDiffs);
  }, [showLoggedMetricDiffs]);

  const loggedMetricsByLabel = useMemo(() => groupLoggedMetricsByLabel(metrics), [metrics]);
  const loggedMetricAccordionKeys = useMemo(
    () => loggedMetricsByLabel.map((group) => accordionItemValueForLoggedLabelGroup(group.label)),
    [loggedMetricsByLabel]
  );
  const [collapsedAccordionKeys, setCollapsedAccordionKeys] = useState<string[]>(() =>
    readStoredCollapsedLoggedMetricGroups(projectId)
  );

  useEffect(() => {
    setCollapsedAccordionKeys(readStoredCollapsedLoggedMetricGroups(projectId));
  }, [projectId]);

  useEffect(() => {
    writeStoredCollapsedLoggedMetricGroups(projectId, collapsedAccordionKeys);
  }, [projectId, collapsedAccordionKeys]);

  const openAccordionKeys = useMemo(
    () => loggedMetricAccordionKeys.filter((key) => !collapsedAccordionKeys.includes(key)),
    [loggedMetricAccordionKeys, collapsedAccordionKeys]
  );

  const handleOpenAccordionKeysChange = (nextOpen: string[]) => {
    setCollapsedAccordionKeys(
      loggedMetricAccordionKeys.filter((key) => !nextOpen.includes(key))
    );
  };

  const hasParentLoggedMetrics = (parentLoggedMetrics?.length ?? 0) > 0;

  /* eslint-disable react-hooks/set-state-in-effect -- reset drafts when metrics refetch */
  useEffect(() => {
    const nextVal: Record<string, string> = {};
    for (const metric of metrics ?? []) {
      nextVal[metric.id] = formatMetricScalarForEditorDraft(metric.value);
    }
    setDraftValues(nextVal);
  }, [metrics]);
  /* eslint-enable react-hooks/set-state-in-effect */

  const invalidateMetrics = () => {
    queryClient.invalidateQueries({ queryKey: [QUERY_KEYS.METRICS.GET(experimentId)] });
    queryClient.invalidateQueries({ queryKey: [QUERY_KEYS.METRICS.BY_PROJECT(projectId)] });
  };

  const upsertMetricMutation = useMutation({
    mutationFn: metricsService.upsert,
    onSuccess: invalidateMetrics,
  });

  const deleteMetricMutation = useMutation({
    mutationFn: metricsService.delete,
    onSuccess: invalidateMetrics,
  });

  const handleRemoveMetric = async (metricId: string) => {
    await deleteMetricMutation.mutateAsync(metricId);
    toast({ title: "Metric removed" });
  };

  const openAddNewLabel = () => {
    setAddMode("new-label");
    setAddGroupLabel(null);
    setNewName("");
    setNewLabel("");
    setNewValue("0");
    setAddOpen(true);
  };

  const openAddToGroup = (groupLabel: string | null) => {
    setAddMode("group");
    setAddGroupLabel(groupLabel);
    setNewName("");
    setNewLabel(groupLabel ?? "");
    setNewValue("0");
    setAddOpen(true);
  };

  const flushValue = async (metric: Metric) => {
    const raw = draftValues[metric.id];
    if (raw === undefined) return;
    const trimmed = raw.trim();
    const num = parseLoggedMetricValueInput(trimmed);
    if (num === null) {
      toast({ title: "Value can't be parsed", variant: "destructive" });
      setDraftValues((prev) => ({
        ...prev,
        [metric.id]: formatMetricScalarForEditorDraft(metric.value),
      }));
      return;
    }
    const short = formatMetricScalarForEditorDraft(metric.value);
    if (trimmed === short || Object.is(num, metric.value)) {
      setDraftValues((prev) => ({ ...prev, [metric.id]: short }));
      return;
    }
    await upsertMetricMutation.mutateAsync({
      experimentId,
      name: metric.name,
      value: num,
      label: metric.label,
    });
    toast({ title: "Metric updated" });
  };

  const handleAdd = async () => {
    if (!newName.trim()) {
      toast({ title: "Name is required", variant: "destructive" });
      return;
    }
    const num = parseLoggedMetricValueInput(newValue.trim());
    if (num === null) {
      toast({ title: "Value can't be parsed", variant: "destructive" });
      return;
    }
    let label: string | null;
    if (addMode === "new-label") {
      const trimmed = newLabel.trim();
      label = trimmed ? trimmed : null;
    } else {
      label = addGroupLabel;
    }
    await upsertMetricMutation.mutateAsync({
      experimentId,
      name: newName.trim(),
      value: num,
      label,
    });
    toast({ title: "Metric added" });
    setAddOpen(false);
    setNewName("");
    setNewLabel("");
    setNewValue("0");
  };

  const renderLoggedMetricRow = (loggedMetric: Metric) => {
    const trackedDefinition = findTrackedDefinitionForLoggedMetric(
      trackedMetricDefinitions,
      loggedMetric
    );
    const isTracked = Boolean(trackedDefinition);
    const showUntrackedDiff = showLoggedMetricDiffs && !isTracked;
    const showDiff = isTracked || showUntrackedDiff;
    const parentValue =
      isTracked && trackedDefinition
        ? lookupLoggedMetricValue(
            parentLoggedMetrics,
            trackedDefinition.name,
            trackedDefinition.label ?? null
          )
        : showUntrackedDiff
          ? lookupLoggedMetricValue(
              parentLoggedMetrics,
              loggedMetric.name,
              loggedMetric.label ?? null
            )
          : null;
    const valueOverride =
      editMode ? (
        <SidebarEditableMetricValue
          metric={loggedMetric}
          draftValues={draftValues}
          setDraftValues={setDraftValues}
          onFlush={flushValue}
        />
      ) : undefined;

    const removeButton = editMode ? (
      <div className={METRIC_SIDEBAR_ROW_REMOVE_CELL_CLASS}>
        <Button
          type="button"
          variant="ghost"
          size="icon"
          className={METRIC_SIDEBAR_ROW_REMOVE_BUTTON_CLASS}
          aria-label="Remove metric"
          disabled={deleteMetricMutation.isPending}
          onClick={() => void handleRemoveMetric(loggedMetric.id)}
          data-testid={`metric-remove-${loggedMetric.id}`}
        >
          <X className={METRIC_SIDEBAR_ROW_REMOVE_ICON_CLASS} />
        </Button>
      </div>
    ) : null;

    const rowClassNames = trackedDefinition
      ? METRIC_SIDEBAR_DENSE_CLASS_NAMES
      : METRIC_SIDEBAR_UNTRACKED_CLASS_NAMES;

    return (
      <MetricNameValueDiffRow
        key={loggedMetric.id}
        metricName={trackedDefinition ? trackedDefinition.name : loggedMetric.name}
        metricLabel={trackedDefinition ? trackedDefinition.label ?? null : loggedMetric.label}
        nameTitleMode="name-only"
        value={loggedMetric.value}
        parentValue={parentValue}
        direction={
          trackedDefinition
            ? trackedDefinition.direction === "minimize"
              ? "minimize"
              : "maximize"
            : "maximize"
        }
        showDirectionHint={Boolean(trackedDefinition)}
        showDiff={showDiff}
        colorizeDiffOutcome={isTracked}
        metricTable={{
          scope: "group",
          groupHasAnyDiff: hasParentLoggedMetrics,
        }}
        classNameProps={rowClassNames}
        valueOverride={valueOverride}
        rowHover
        trailing={removeButton}
        data-testid={`logged-metric-${loggedMetric.id}`}
      />
    );
  };

  if (metricsLoading) {
    return <Skeleton className="h-24 w-full" />;
  }

  return (
    <>
      <Card>
        <CardHeader className="flex min-w-0 flex-row items-center justify-between gap-2 px-3 py-2">
          <CardTitle className="min-w-0 truncate text-xs font-medium text-muted-foreground">
            Logged Metrics
          </CardTitle>
          <LoggedMetricsHeaderActions
            hasParentLoggedMetrics={hasParentLoggedMetrics}
            showLoggedMetricDiffs={showLoggedMetricDiffs}
            onToggleDiffs={() => setShowLoggedMetricDiffs((enabled) => !enabled)}
            onAddNewLabel={openAddNewLabel}
            editMode={editMode}
            onToggleEditMode={() => setEditMode((enabled) => !enabled)}
            includeExpand
            onExpand={() => setExpandedOpen(true)}
          />
        </CardHeader>
        <CardContent className="space-y-3 px-3 pb-3 pt-0">
          <LoggedMetricsList
            loggedMetricsByLabel={loggedMetricsByLabel}
            openAccordionKeys={openAccordionKeys}
            onOpenAccordionKeysChange={handleOpenAccordionKeysChange}
            hasParentLoggedMetrics={hasParentLoggedMetrics}
            editMode={editMode}
            renderLoggedMetricRow={renderLoggedMetricRow}
            onAddToGroup={openAddToGroup}
          />
        </CardContent>
      </Card>

      <LoggedMetricsExpandedModal
        open={expandedOpen}
        onOpenChange={setExpandedOpen}
        loggedMetricsByLabel={loggedMetricsByLabel}
        openAccordionKeys={openAccordionKeys}
        onOpenAccordionKeysChange={handleOpenAccordionKeysChange}
        hasParentLoggedMetrics={hasParentLoggedMetrics}
        editMode={editMode}
        renderLoggedMetricRow={renderLoggedMetricRow}
        onAddToGroup={openAddToGroup}
        showLoggedMetricDiffs={showLoggedMetricDiffs}
        onToggleDiffs={() => setShowLoggedMetricDiffs((enabled) => !enabled)}
        onAddNewLabel={openAddNewLabel}
        onToggleEditMode={() => setEditMode((enabled) => !enabled)}
      />

      <LoggedMetricAddDialog
        open={addOpen}
        onOpenChange={setAddOpen}
        mode={addMode}
        groupLabel={addGroupLabel}
        newName={newName}
        onNewNameChange={setNewName}
        newLabel={newLabel}
        onNewLabelChange={setNewLabel}
        newValue={newValue}
        onNewValueChange={setNewValue}
        onAdd={handleAdd}
      />
    </>
  );
}
