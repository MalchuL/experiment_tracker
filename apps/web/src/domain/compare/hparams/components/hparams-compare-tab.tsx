"use client";

import { keepPreviousData, useQuery } from "@tanstack/react-query";
import { Button } from "@/components/ui/button";
import {
  ExperimentDataCompareTable,
  ExperimentDataDiffValue,
  type ExperimentDataCompareColumn,
  type ExperimentDataCompareRow,
  type ExperimentDataDiffStatus,
} from "@/domain/compare/components/experiment-data-compare-table";
import { InlineDiffText } from "@/domain/compare/snapshots/components/inline-diff-text";
import type { Experiment } from "@/domain/experiments/types";
import type { JsonValue } from "@/domain/experiments/types";
import { QUERY_KEYS } from "@/lib/constants/query-keys";
import { buildHparamsCompareRows } from "../lib/hparams-compare";
import { hparamsListService } from "../services/hparams-list-service";

export function HparamsCompareTab({
  projectId,
  allExperiments,
  selectedExperiments,
  onEnsureExperimentSelected,
}: {
  projectId: string;
  allExperiments: Experiment[];
  selectedExperiments: Experiment[];
  onEnsureExperimentSelected: (experimentId: string) => void;
}) {
  const experimentIds = selectedExperiments.map((experiment) => experiment.id);
  const latestExperiment = allExperiments[0] ?? null;
  const query = useQuery({
    queryKey: [QUERY_KEYS.PROJECTS.HPARAMS_LIST(projectId, experimentIds)],
    queryFn: () => hparamsListService.list(projectId, experimentIds),
    enabled: experimentIds.length > 0,
    placeholderData: keepPreviousData,
  });

  if (experimentIds.length === 0) {
    return (
      <Centered className="flex-col gap-3 text-center">
        <span>
          Please select an experiment to browse its hyperparameters
          {latestExperiment ? ", or choose the latest experiment." : "."}
        </span>
        {latestExperiment ? (
          <Button
            type="button"
            variant="outline"
            size="sm"
            onClick={() => onEnsureExperimentSelected(latestExperiment.id)}
          >
            Choose {latestExperiment.name}
          </Button>
        ) : null}
      </Centered>
    );
  }
  if (!query.data) {
    return query.isError
      ? <Centered>Failed to load hyperparameters.</Centered>
      : <Centered>Loading hyperparameters...</Centered>;
  }

  const hparamsRows = buildHparamsCompareRows(query.data.experiments);
  if (hparamsRows.length === 0) return <Centered>No selected experiment has hyperparameters.</Centered>;

  const columns: ExperimentDataCompareColumn[] = query.data.experiments.map((experiment) => ({
    id: experiment.experimentId,
    label: experiment.experimentName,
    secondaryLabel: experiment.hparams === null ? "No HParams" : undefined,
  }));
  const rows: ExperimentDataCompareRow<JsonValue>[] = hparamsRows.map((row) => ({
    id: row.pathKey,
    label: row.pathKey,
    depth: Math.max(0, row.path.length - 1),
    values: row.values,
  }));

  return (
    <ExperimentDataCompareTable
      storageScope={`hparams:${projectId}`}
      leadColumnLabel="Parameter"
      columns={columns}
      rows={rows}
      renderValue={renderHparamsValue}
      valueTitle={(value, _referenceValue, _status, _row) => displayHparamsValue(value)}
      defaultOverflowMode="wrap"
    />
  );
}

function renderHparamsValue(
  value: JsonValue | undefined,
  referenceValue: JsonValue | undefined,
  status: ExperimentDataDiffStatus,
  _row: ExperimentDataCompareRow<JsonValue>
) {
  if (status === "changed" && referenceValue !== undefined && value !== undefined) {
    return (
      <ExperimentDataDiffValue status={status}>
        <InlineDiffText
          content={displayHparamsValue(value)}
          compareWith={displayHparamsValue(referenceValue)}
          side="new"
          language="json"
          className="text-xs text-foreground"
        />
      </ExperimentDataDiffValue>
    );
  }

  return (
    <ExperimentDataDiffValue status={status}>
      <code
        className={
          status === "removed" || status === "missing"
            ? "text-xs text-muted-foreground"
            : "text-xs text-foreground"
        }
      >
        {displayHparamsValue(value)}
      </code>
    </ExperimentDataDiffValue>
  );
}

function displayHparamsValue(value: JsonValue | undefined): string {
  return value === undefined ? "Not set" : JSON.stringify(value);
}

function Centered({
  children,
  className = "",
}: {
  children: React.ReactNode;
  className?: string;
}) {
  return (
    <div
      className={`flex min-h-0 flex-1 items-center justify-center p-8 text-sm text-muted-foreground ${className}`}
    >
      {children}
    </div>
  );
}
