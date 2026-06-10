"use client";

import { Fragment, useEffect, useMemo, useState, type Dispatch, type SetStateAction } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import * as AccordionPrimitive from "@radix-ui/react-accordion";
import { ChevronDown, Plus, X } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Accordion,
  AccordionContent,
  AccordionItem,
} from "@/components/ui/accordion";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Skeleton } from "@/components/ui/skeleton";
import { Switch } from "@/components/ui/switch";
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

function lookupLoggedMetricValue(
  metrics: Metric[] | undefined,
  trackedMetric: ProjectMetric
): number | null | undefined {
  const matchedRow = metrics?.find((row) =>
    displayMetricKeyEquals(
      { name: row.name, label: row.label ?? null },
      { name: trackedMetric.name, label: trackedMetric.label ?? null }
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

  const loggedMetricsByLabel = useMemo(() => groupLoggedMetricsByLabel(metrics), [metrics]);
  const defaultOpenLoggedMetricAccordionKeys = useMemo(
    () => loggedMetricsByLabel.map((group) => accordionItemValueForLoggedLabelGroup(group.label)),
    [loggedMetricsByLabel]
  );

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

  const renderLoggedMetricRow = (
    loggedMetric: Metric,
    loggedLabelGroupShowsParentDelta: boolean
  ) => {
    const trackedDefinition = findTrackedDefinitionForLoggedMetric(
      trackedMetricDefinitions,
      loggedMetric
    );
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

    if (trackedDefinition) {
      return (
        <Fragment key={loggedMetric.id}>
          <MetricNameValueDiffRow
            metricName={trackedDefinition.name}
            metricLabel={trackedDefinition.label ?? null}
            nameTitleMode="name-only"
            value={loggedMetric.value}
            parentValue={lookupLoggedMetricValue(parentLoggedMetrics, trackedDefinition)}
            direction={trackedDefinition.direction === "minimize" ? "minimize" : "maximize"}
            showDirectionHint
            metricTable={{
              scope: "group",
              groupHasAnyDiff: loggedLabelGroupShowsParentDelta,
            }}
            classNameProps={METRIC_SIDEBAR_DENSE_CLASS_NAMES}
            valueOverride={valueOverride}
            data-testid={`logged-metric-${loggedMetric.id}`}
          />
          {removeButton}
        </Fragment>
      );
    }

    return (
      <Fragment key={loggedMetric.id}>
        <MetricNameValueDiffRow
          metricName={loggedMetric.name}
          metricLabel={loggedMetric.label}
          nameTitleMode="name-only"
          value={loggedMetric.value}
          parentValue={null}
          direction="maximize"
          showDiff={false}
          metricTable={{
            scope: "group",
            groupHasAnyDiff: loggedLabelGroupShowsParentDelta,
          }}
          classNameProps={METRIC_SIDEBAR_UNTRACKED_CLASS_NAMES}
          valueOverride={valueOverride}
          data-testid={`logged-metric-${loggedMetric.id}`}
        />
        {removeButton}
      </Fragment>
    );
  };

  if (metricsLoading) {
    return <Skeleton className="h-24 w-full" />;
  }

  return (
    <>
      <Card>
        <CardHeader className="py-2 px-3">
          <CardTitle className="text-xs font-medium text-muted-foreground">Logged Metrics</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3 px-3 pb-3 pt-0">
          {loggedMetricsByLabel.length === 0 ? (
            <p className="py-2 text-center text-sm text-muted-foreground">No metrics logged yet</p>
          ) : (
            <Accordion type="multiple" className="w-full" defaultValue={defaultOpenLoggedMetricAccordionKeys}>
              {loggedMetricsByLabel.map((labelGroup) => {
                const accordionItemValue = accordionItemValueForLoggedLabelGroup(labelGroup.label);
                const groupTitle =
                  labelGroup.label != null && labelGroup.label !== ""
                    ? labelGroup.label
                    : "Unlabeled";
                const loggedLabelGroupShowsParentDelta = labelGroup.items.some((loggedMetric) => {
                  const trackedDefinition = findTrackedDefinitionForLoggedMetric(
                    trackedMetricDefinitions,
                    loggedMetric
                  );
                  if (!trackedDefinition) return false;
                  const parentScalar = lookupLoggedMetricValue(
                    parentLoggedMetrics,
                    trackedDefinition
                  );
                  return loggedMetric.value != null && parentScalar != null;
                });

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
                        onClick={() => openAddToGroup(labelGroup.label)}
                      >
                        <Plus className="h-4 w-4" />
                      </Button>
                    </AccordionPrimitive.Header>
                    <AccordionContent className="pb-2 pt-0">
                      <div
                        className={loggedMetricRowGroupTableClass(
                          loggedLabelGroupShowsParentDelta,
                          editMode
                        )}
                      >
                        {labelGroup.items.map((loggedMetric) =>
                          renderLoggedMetricRow(loggedMetric, loggedLabelGroupShowsParentDelta)
                        )}
                      </div>
                    </AccordionContent>
                  </AccordionItem>
                );
              })}
            </Accordion>
          )}

          <div className="flex flex-wrap items-center justify-between gap-x-3 gap-y-2 border-t border-border/50 pt-3">
            <Button
              type="button"
              size="sm"
              variant="outline"
              className="h-8 text-xs"
              onClick={openAddNewLabel}
              data-testid="button-add-metric-label"
            >
              Add label & metric
            </Button>
            <div className="flex items-center gap-2">
              <Switch
                id="sidebar-logged-metrics-edit-mode"
                checked={editMode}
                onCheckedChange={setEditMode}
                data-testid="switch-sidebar-logged-metrics-edit-mode"
              />
              <Label htmlFor="sidebar-logged-metrics-edit-mode" className="text-sm font-normal">
                Edit existing metrics
              </Label>
            </div>
          </div>
        </CardContent>
      </Card>

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
