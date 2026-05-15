"use client";

/**
 * Project DAG view: experiment lineage as a React Flow graph with draggable nodes, persisted layout
 * (``dag-layout-store``), metric deltas vs parent, search/highlight, and parent reassignment with cycle checks.
 */

import {
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
  type MouseEvent,
} from "react";
import {
  ReactFlow,
  Node,
  Edge,
  Controls,
  Background,
  useNodesState,
  useEdgesState,
  Handle,
  Position,
  MiniMap,
  Panel,
  ReactFlowProvider,
  useReactFlow,
  MarkerType,
  type Connection,
  type NodeChange,
  type OnNodesChange,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import { EmptyState } from "@/components/shared/empty-state";
import { ExperimentSidebar } from "@/components/shared/experiment-sidebar";
import { useCurrentProject } from "@/domain/projects/hooks";
import { useExperiments, useAggregatedMetrics } from "@/domain/experiments/hooks";
import {
  useSelectedExperimentStore,
  useDagLayoutStore,
  EMPTY_DAG_LAYOUT_POSITIONS,
} from "@/domain/experiments/store";
import { experimentsService } from "@/domain/experiments/services";
import type { Experiment } from "@/domain/experiments/types";
import type { Project, ProjectMetric } from "@/domain/projects/types";
import {
  GitBranch,
  Clock,
  Play,
  CheckCircle2,
  XCircle,
  AlertCircle,
  RefreshCw,
  Search,
  X,
  LayoutGrid,
  Loader2,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { DAG_NODE_MAX_DISPLAY_METRICS, DAG_NODE_WIDTH_PX } from "@/lib/constants/dag";
import { REFRESH_EXPERIMENTS_LIST_INTERVAL } from "@/lib/constants/rates";
import { Metric } from "@/domain/metrics/types";
import {
  displayMetricKeyEquals,
  formatMetricLabel,
  getDisplayedTrackedMetrics,
  projectMetricKeyString,
} from "@/lib/metrics/format-metric-label";
import { MetricDeltaVsParent } from "@/components/shared/metric-delta-vs-parent";
import { formatMetricScalarForDisplay } from "@/lib/metrics/metric-value-display";
import { cn } from "@/lib/utils";
import { useQueryClient } from "@tanstack/react-query";
import { QUERY_KEYS } from "@/lib/constants/query-keys";
import { useToast } from "@/lib/hooks/use-toast";
import { calculateDagTreeLayout } from "@/domain/experiments/dag/calculate-dag-layout";
import { wouldCreateCycle } from "@/domain/experiments/dag/dag-parent-utils";
import { ListSkeleton } from "@/components/shared/loading-skeleton";
import type { InsertExperiment } from "@/domain/experiments/types";

export interface MetricComparison {
  name: string;
  label: string | null;
  value: number | null;
  parentValue: number | null;
  direction: "maximize" | "minimize";
}

export interface ExperimentNodeData {
  id: string;
  label: string;
  description: string;
  status: string;
  color: string;
  progress: number;
  metrics: MetricComparison[];
  isSelected?: boolean;
  isHighlighted?: boolean;
  [key: string]: unknown;
}

function buildMetricComparisons(
  exp: Experiment,
  aggregatedMetricsByExperiment: Record<string, Metric[]> | undefined,
  project: Project | null | undefined
): MetricComparison[] {
  const projectMetrics = project?.metrics?.trackedMetrics ?? [];
  const dimensionsToDisplay = !project?.metrics
    ? []
    : getDisplayedTrackedMetrics(
        project.metrics.trackedMetrics,
        project.metrics.displayMetrics
      ).map((m) => ({
        name: m.name,
        label: m.label ?? null,
      }));

  const expMetrics = aggregatedMetricsByExperiment?.[exp.id] ?? [];
  const parentMetrics: Metric[] = exp.parentExperimentId
    ? aggregatedMetricsByExperiment?.[exp.parentExperimentId] ?? []
    : [];

  return dimensionsToDisplay.map((dim) => {
    const pm = projectMetrics.find((m) =>
      displayMetricKeyEquals({ name: m.name, label: m.label ?? null }, dim)
    );
    const value =
      expMetrics?.find((m) =>
        displayMetricKeyEquals({ name: m.name, label: m.label }, dim)
      )?.value ?? null;
    const parentValue =
      parentMetrics?.find((m) =>
        displayMetricKeyEquals({ name: m.name, label: m.label }, dim)
      )?.value ?? null;
    const direction = pm?.direction || "maximize";

    return {
      name: dim.name,
      label: dim.label,
      value,
      parentValue,
      direction,
    };
  });
}

function ExperimentNode({ data }: { data: ExperimentNodeData }) {
  const getStatusIcon = (status: string) => {
    switch (status) {
      case "running":
        return <Play className="w-3 h-3 text-blue-500 shrink-0" />;
      case "complete":
        return <CheckCircle2 className="w-3 h-3 text-green-500 shrink-0" />;
      case "failed":
        return <XCircle className="w-3 h-3 text-red-500 shrink-0" />;
      default:
        return <Clock className="w-3 h-3 shrink-0" />;
    }
  };

  const shownMetrics = data.metrics.slice(0, DAG_NODE_MAX_DISPLAY_METRICS);
  const restCount = data.metrics.length - shownMetrics.length;

  const highlightOpacity =
    data.isHighlighted === false ? ({ opacity: 0.35 } as const) : undefined;

  return (
    <>
      <Handle type="target" position={Position.Top} className="w-2 h-2" />
      <div
        className={cn(
          "min-w-0 shrink-0 px-2 py-1.5 rounded-md border bg-card shadow-sm cursor-pointer hover-elevate transition-all",
          data.isSelected && "ring-2 ring-primary ring-offset-2 ring-offset-background"
        )}
        style={{
          width: DAG_NODE_WIDTH_PX,
          borderLeftColor: data.color,
          borderLeftWidth: "4px",
          ...highlightOpacity,
        }}
        data-testid={`dag-node-${data.id}`}
        aria-selected={data.isSelected === true}
      >
        <Tooltip>
          <TooltipTrigger asChild>
            <div className="flex items-center gap-1.5 mb-0.5 min-w-0">
              <div
                className="w-2 h-2 rounded-full shrink-0"
                style={{ backgroundColor: data.color }}
              />
              <span className="text-xs font-medium truncate flex-1 min-w-0">
                {data.label}
              </span>
              {getStatusIcon(data.status)}
            </div>
          </TooltipTrigger>
          <TooltipContent side="top" className="max-w-sm">
            <p className="font-medium break-words">{data.label}</p>
          </TooltipContent>
        </Tooltip>

        {data.description ? (
          <Tooltip>
            <TooltipTrigger asChild>
              <p className="text-[10px] text-muted-foreground line-clamp-2 leading-tight mb-0.5">
                {data.description}
              </p>
            </TooltipTrigger>
            <TooltipContent side="bottom" className="max-w-sm">
              <p className="text-xs break-words">{data.description}</p>
            </TooltipContent>
          </Tooltip>
        ) : null}

        {shownMetrics.length > 0 && (
          <div className="flex flex-col gap-0 mt-1 border-t pt-0.5 leading-tight">
            {shownMetrics.map((metric) => {
              const labelText = formatMetricLabel(metric.name, metric.label);
              return (
                <div
                  key={projectMetricKeyString({
                    name: metric.name,
                    label: metric.label,
                  })}
                  className="flex items-center gap-0.5 text-[10px] min-w-0"
                >
                  <Tooltip>
                    <TooltipTrigger asChild>
                      <span className="text-muted-foreground truncate min-w-0 flex-1">
                        {labelText}
                      </span>
                    </TooltipTrigger>
                    <TooltipContent side="left" className="max-w-xs">
                      {labelText}
                    </TooltipContent>
                  </Tooltip>
                  <div className="flex items-center gap-0.5 shrink-0">
                    <span className="font-mono tabular-nums text-[10px]">
                      {formatMetricScalarForDisplay(metric.value)}
                    </span>
                    <MetricDeltaVsParent
                      value={metric.value}
                      parentValue={metric.parentValue}
                      direction={metric.direction}
                    />
                  </div>
                </div>
              );
            })}
            {restCount > 0 ? (
              <span className="text-[9px] text-muted-foreground">+{restCount} more</span>
            ) : null}
          </div>
        )}

        {data.status === "running" && (
          <div className="mt-1 h-0.5 bg-muted rounded-full overflow-hidden">
            <div
              className="h-full bg-blue-500 rounded-full"
              style={{ width: `${data.progress}%` }}
            />
          </div>
        )}
      </div>
      <Handle type="source" position={Position.Bottom} className="w-2 h-2" />
    </>
  );
}

const nodeTypes = { experiment: ExperimentNode };

/**
 * Inner React Flow canvas: merges persisted DAG coordinates from ``useDagLayoutStore`` with
 * ``calculateDagTreeLayout``, wires metrics onto nodes, parent edits, and keeps RF nodes/edges in sync
 * with computed layout (see ``experimentsStructureKey`` for edge refresh).
 */
function DagViewCanvas({
  projectId,
  project,
  experiments,
  aggregatedMetricsByExperiment,
  filteredMetrics,
  refetchExperiments,
  refetchMetrics,
  experimentsFetching,
  metricsFetching,
  experimentsStillPaging,
}: {
  projectId: string;
  project: Project | null | undefined;
  experiments: Experiment[];
  aggregatedMetricsByExperiment: Record<string, Metric[]> | undefined;
  filteredMetrics: ProjectMetric[];
  refetchExperiments: () => Promise<unknown>;
  refetchMetrics: () => Promise<unknown>;
  experimentsFetching: boolean;
  metricsFetching: boolean;
  experimentsStillPaging: boolean;
}) {
  const queryClient = useQueryClient();
  const { toast } = useToast();
  const { fitView } = useReactFlow();
  const savedPositions = useDagLayoutStore(
    (s) => s.layoutsByProject[projectId] ?? EMPTY_DAG_LAYOUT_POSITIONS
  );
  const updateNodePosition = useDagLayoutStore((s) => s.updateNodePosition);
  const replaceProjectLayout = useDagLayoutStore((s) => s.replaceProjectLayout);

  const { selectedExperimentId, setSelectedExperimentId } = useSelectedExperimentStore();
  const [searchQuery, setSearchQuery] = useState("");
  /** Node ids currently mid-drag — avoids syncing layout-derived nodes over RF state (error #015). */
  const draggingNodeIdsRef = useRef<Set<string>>(new Set());

  const layout = useMemo(
    () => calculateDagTreeLayout(experiments, savedPositions),
    [experiments, savedPositions]
  );

  /** Persist resolved coordinates for every experiment on the canvas (not only dragged nodes). */
  useEffect(() => {
    replaceProjectLayout(projectId, layout.positionsById);
  }, [projectId, layout.positionsById, replaceProjectLayout]);

  const nodeDataById = useMemo(() => {
    const map = new Map<string, ExperimentNodeData>();
    for (const exp of experiments) {
      const metrics = buildMetricComparisons(
        exp,
        aggregatedMetricsByExperiment,
        project
      );
      const q = searchQuery.trim().toLowerCase();
      const matches =
        !q ||
        exp.name.toLowerCase().includes(q) ||
        (exp.description?.toLowerCase().includes(q) ?? false);
      map.set(exp.id, {
        id: exp.id,
        label: exp.name,
        description: exp.description || "",
        status: exp.status,
        color: exp.color,
        progress: exp.progress,
        metrics,
        isSelected: selectedExperimentId === exp.id,
        isHighlighted: searchQuery ? matches : undefined,
      });
    }
    return map;
  }, [
    experiments,
    aggregatedMetricsByExperiment,
    project,
    searchQuery,
    selectedExperimentId,
  ]);

  const computedNodes = useMemo((): Node<ExperimentNodeData>[] => {
    return experiments.map((exp) => {
      const pos = layout.positionsById[exp.id] ?? { x: 0, y: 0 };
      const data = nodeDataById.get(exp.id)!;
      return {
        id: exp.id,
        type: "experiment",
        position: pos,
        data,
      };
    });
  }, [experiments, layout.positionsById, nodeDataById]);

  const [nodes, setNodes, onNodesChange] = useNodesState<Node<ExperimentNodeData>>([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState<Edge>(layout.edges);

  /**
   * Keep node data in sync with experiments/search/selection. While a node is being dragged, preserve its
   * live position from React Flow instead of overwriting from layout (which only updates after drag end).
   */
  useEffect(() => {
    setNodes((prevNodes) => {
      const prevById = new Map(prevNodes.map((n) => [n.id, n]));
      const dragging = draggingNodeIdsRef.current;
      return computedNodes.map((cn) => {
        const prev = prevById.get(cn.id);
        if (prev && dragging.has(cn.id)) {
          return { ...cn, position: prev.position };
        }
        return cn;
      });
    });
  }, [computedNodes, setNodes]);

  const experimentsStructureKey = useMemo(
    () =>
      experiments
        .map(
          (e) =>
            `${e.id}:${e.parentExperimentId ?? "-"}:${e.status}:${e.color ?? ""}`
        )
        .sort()
        .join("|"),
    [experiments]
  );

  useEffect(() => {
    setEdges(layout.edges);
  }, [experimentsStructureKey, layout.edges, setEdges]);

  const handleNodesChange: OnNodesChange<Node<ExperimentNodeData>> = useCallback(
    (changes: NodeChange<Node<ExperimentNodeData>>[]) => {
      onNodesChange(changes);
      if (!projectId) return;
      for (const change of changes) {
        if (change.type !== "position" || !change.position) continue;
        if (change.dragging === true) {
          draggingNodeIdsRef.current.add(change.id);
          continue;
        }
        if (change.dragging === false) {
          draggingNodeIdsRef.current.delete(change.id);
          updateNodePosition(projectId, change.id, change.position);
        }
      }
    },
    [onNodesChange, projectId, updateNodePosition]
  );

  const handleResetLayout = useCallback(() => {
    useDagLayoutStore.getState().clearProjectLayout(projectId);
    setTimeout(() => {
      fitView({ padding: 0.2 });
    }, 50);
  }, [projectId, fitView]);

  const applyParentUpdate = useCallback(
    async (childId: string, newParentId: string | null) => {
      await experimentsService.update(childId, {
        parentExperimentId: newParentId,
      } as unknown as InsertExperiment);
      await queryClient.invalidateQueries({
        queryKey: [QUERY_KEYS.EXPERIMENTS.BY_PROJECT(projectId)],
      });
      await queryClient.invalidateQueries({
        queryKey: [QUERY_KEYS.EXPERIMENTS.BY_ID(childId)],
      });
    },
    [queryClient, projectId]
  );

  const onConnect = useCallback(
    async (connection: Connection) => {
      const { source, target } = connection;
      if (!source || !target || source === target) return;

      if (wouldCreateCycle(experiments, target, source)) {
        toast({
          title: "Invalid connection",
          description: "This link would create a cycle in the experiment tree.",
          variant: "destructive",
        });
        return;
      }

      try {
        await applyParentUpdate(target, source);
        toast({ title: "Parent updated" });
      } catch (e) {
        toast({
          title: "Could not update parent",
          description: e instanceof Error ? e.message : "Request failed",
          variant: "destructive",
        });
      }
    },
    [experiments, applyParentUpdate, toast]
  );

  const onEdgesDelete = useCallback(
    (deleted: Edge[]) => {
      if (deleted.length === 0) return;
      for (const edge of deleted) {
        const targetId = edge.target;
        if (!targetId) continue;
        void (async () => {
          try {
            await applyParentUpdate(targetId, null);
            toast({ title: "Parent link removed" });
          } catch (e) {
            toast({
              title: "Could not remove parent",
              description: e instanceof Error ? e.message : "Request failed",
              variant: "destructive",
            });
            await refetchExperiments();
          }
        })();
      }
    },
    [applyParentUpdate, toast, refetchExperiments]
  );

  const onNodeClick = useCallback(
    (_: MouseEvent, node: Node) => {
      setSelectedExperimentId(node.id);
    },
    [setSelectedExperimentId]
  );

  const isRefreshing = experimentsFetching || metricsFetching;
  const handleRefresh = () => {
    void Promise.all([refetchExperiments(), refetchMetrics()]);
  };

  return (
    <>
      <div className="dag-flow-canvas h-full min-h-[480px] w-full relative">
        <TooltipProvider delayDuration={300}>
          <ReactFlow
            nodes={nodes}
            edges={edges}
            onNodesChange={handleNodesChange}
            onEdgesChange={onEdgesChange}
            onConnect={onConnect}
            onEdgesDelete={onEdgesDelete}
            onNodeClick={onNodeClick}
            nodeTypes={nodeTypes}
            fitView
            fitViewOptions={{ padding: 0.15 }}
            minZoom={0.15}
            maxZoom={2}
            proOptions={{ hideAttribution: true }}
            deleteKeyCode={["Backspace", "Delete"]}
            elevateEdgesOnSelect
            defaultEdgeOptions={{
              type: "smoothstep",
              style: { strokeWidth: 1.75 },
              markerEnd: {
                type: MarkerType.ArrowClosed,
                markerUnits: "userSpaceOnUse",
                width: 11,
                height: 11,
              },
            }}
          >
            <Background gap={20} className="bg-muted/20" />
            <MiniMap
              className="!bg-card border rounded-md"
              nodeColor={(node) => {
                const st = node.data?.status as string | undefined;
                if (st === "running") return "hsl(var(--primary))";
                if (st === "complete") return "hsl(142 76% 36%)";
                if (st === "failed") return "hsl(var(--destructive))";
                return "hsl(var(--muted-foreground))";
              }}
              maskColor="hsl(var(--background) / 0.75)"
            />
            <Panel position="top-left" className="m-2">
              <div className="flex items-center gap-2 bg-card/95 p-2 rounded-md border shadow-sm">
                <Search className="h-4 w-4 text-muted-foreground shrink-0" />
                <Input
                  placeholder="Search experiments..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="h-8 w-44 sm:w-52 text-sm"
                  data-testid="input-dag-search"
                />
                {searchQuery ? (
                  <Button
                    size="icon"
                    variant="ghost"
                    className="h-6 w-6 shrink-0"
                    onClick={() => setSearchQuery("")}
                    data-testid="button-dag-clear-search"
                    aria-label="Clear search"
                  >
                    <X className="h-3 w-3" />
                  </Button>
                ) : null}
              </div>
            </Panel>
            <Panel position="top-right" className="m-2 flex items-center gap-2">
              {experimentsStillPaging ? (
                <Tooltip>
                  <TooltipTrigger asChild>
                    <div
                      className="flex h-9 w-9 items-center justify-center rounded-md border bg-card/95 shadow-sm"
                      aria-label="Loading more experiments"
                    >
                      <Loader2 className="h-4 w-4 animate-spin text-muted-foreground" />
                    </div>
                  </TooltipTrigger>
                  <TooltipContent side="bottom">Loading more experiments…</TooltipContent>
                </Tooltip>
              ) : null}
              <Button
                variant="outline"
                size="icon"
                onClick={handleResetLayout}
                aria-label="Reset layout"
                title="Reset layout"
                data-testid="button-dag-reset-layout"
              >
                <LayoutGrid className="h-4 w-4" />
              </Button>
              <Button
                variant="outline"
                size="icon"
                onClick={handleRefresh}
                disabled={isRefreshing}
                data-testid="button-refresh-dag"
                aria-label="Refresh DAG"
              >
                <RefreshCw className={isRefreshing ? "animate-spin" : ""} />
              </Button>
            </Panel>
            <Controls position="bottom-right" />
          </ReactFlow>
        </TooltipProvider>
      </div>

      {selectedExperimentId ? (
        <ExperimentSidebar
          variant="overlay"
          experimentId={selectedExperimentId}
          onClose={() => setSelectedExperimentId(null)}
          projectMetrics={filteredMetrics}
          aggregatedMetricsByExperiment={aggregatedMetricsByExperiment}
        />
      ) : null}
    </>
  );
}

export function ProjectDagView() {
  const { project, isLoading: projectLoading } = useCurrentProject();
  const projectId = project?.id;
  const {
    experiments,
    isLoading: experimentsLoading,
    isFetching: experimentsFetching,
    isFetchingNextPage: experimentsFetchingNextPage,
    hasNextPage: experimentsHasNextPage,
    refetch: refetchExperiments,
  } = useExperiments(projectId, {
    refetchInterval: REFRESH_EXPERIMENTS_LIST_INTERVAL,
  });
  const {
    aggregatedMetricsByExperiment,
    isFetching: metricsFetching,
    isLoading: metricsLoading,
    refetch: refetchMetrics,
  } = useAggregatedMetrics(projectId, {
    refetchInterval: REFRESH_EXPERIMENTS_LIST_INTERVAL,
  });

  const filteredMetrics = useMemo(
    () =>
      !project?.metrics
        ? []
        : getDisplayedTrackedMetrics(
            project.metrics.trackedMetrics,
            project.metrics.displayMetrics
          ),
    [project?.metrics]
  );

  const isLoading = projectLoading || experimentsLoading || metricsLoading;

  const experimentsStillPaging =
    Boolean(experimentsHasNextPage) &&
    (experimentsFetchingNextPage || experimentsFetching) &&
    !experimentsLoading;

  if (!projectId) {
    return (
      <div className="flex flex-col items-center justify-center h-[calc(100vh-8rem)] gap-4">
        <AlertCircle className="w-12 h-12 text-muted-foreground" />
        <h2 className="text-lg font-medium">No Project Selected</h2>
        <p className="text-muted-foreground text-center max-w-md">
          Click on the logo in the sidebar to select a project and view its experiment DAG.
        </p>
      </div>
    );
  }

  if (isLoading) {
    return (
      <div className="px-6 pt-6">
        <ListSkeleton count={3} />
      </div>
    );
  }

  if (experiments.length === 0) {
    return (
      <div className="h-full min-h-0 flex flex-col">
        <div className="flex-1 flex items-center justify-center min-h-[400px] px-6">
          <EmptyState
            icon={GitBranch}
            title="No experiments yet"
            description="Create experiments to see their relationships in the DAG view."
          />
        </div>
      </div>
    );
  }

  return (
    <div className="h-full min-h-0 flex flex-col">
      <div className="flex-1 min-h-0">
        <ReactFlowProvider>
          <DagViewCanvas
            projectId={projectId}
            project={project}
            experiments={experiments}
            aggregatedMetricsByExperiment={aggregatedMetricsByExperiment}
            filteredMetrics={filteredMetrics}
            refetchExperiments={refetchExperiments}
            refetchMetrics={refetchMetrics}
            experimentsFetching={experimentsFetching}
            metricsFetching={metricsFetching}
            experimentsStillPaging={experimentsStillPaging}
          />
        </ReactFlowProvider>
      </div>
    </div>
  );
}
