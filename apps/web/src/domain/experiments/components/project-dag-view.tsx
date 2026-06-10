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
  type PointerEvent as ReactPointerEvent,
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
import { useExperiments, useAggregatedMetrics, useOrderedExperimentSelection } from "@/domain/experiments/hooks";
import {
  useSelectedExperimentStore,
  useDagLayoutStore,
  EMPTY_DAG_LAYOUT_POSITIONS,
  EMPTY_DAG_NODE_SIZES,
} from "@/domain/experiments/store";
import { ExperimentSelectionOrderBadge } from "@/domain/experiments/components/experiment-selection-order-badge";
import { ExperimentCompareBar } from "@/domain/experiments/components/experiment-compare-bar";
import { CompareLabeledSwitch } from "@/domain/compare/components/compare-labeled-switch";
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
  ChevronLeft,
  ChevronRight,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { DAG_NODE_HEIGHT_PX, DAG_NODE_MAX_DISPLAY_METRICS, DAG_NODE_WIDTH_PX } from "@/lib/constants/dag";
import { clampDagNodeWidth } from "@/domain/experiments/dag/clamp-dag-node-size";
import { REFRESH_EXPERIMENTS_LIST_INTERVAL } from "@/lib/constants/rates";
import { Metric } from "@/domain/metrics/types";
import {
  displayMetricKeyEquals,
  getDisplayedTrackedMetrics,
  projectMetricKeyString,
} from "@/lib/metrics/format-metric-label";
import {
  MetricNameValueDiffRow,
  metricRowGroupTableClass,
} from "@/components/shared/metric-name-value-diff-row";
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
  isSearchFocus?: boolean;
  selectionMode?: boolean;
  selectionOrder?: number | null;
  onSelectionToggle?: () => void;
  nodeWidth: number;
  onNodeResizeEnd?: (width: number) => void;
  onAfterResizeDrag?: () => void;
  [key: string]: unknown;
}

const DAG_METRIC_ROW_SEPARATOR_CLASS = "border-b border-border/25 py-0.5";

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
  const nodeRef = useRef<HTMLDivElement>(null);
  const liveWidthRef = useRef<number | null>(null);
  const [liveWidth, setLiveWidth] = useState<number | null>(null);

  const width = liveWidth ?? data.nodeWidth;

  const handleResizePointerDown = (event: ReactPointerEvent<HTMLDivElement>) => {
    event.stopPropagation();
    event.preventDefault();
    const element = nodeRef.current;
    if (!element || !data.onNodeResizeEnd) return;

    const startX = event.clientX;
    const startWidth = element.getBoundingClientRect().width;
    const onNodeResizeEnd = data.onNodeResizeEnd;
    const onAfterResizeDrag = data.onAfterResizeDrag;
    let didDrag = false;

    const onPointerMove = (moveEvent: PointerEvent) => {
      if (Math.abs(moveEvent.clientX - startX) > 2) {
        didDrag = true;
      }
      const nextWidth = clampDagNodeWidth(startWidth + (moveEvent.clientX - startX));
      liveWidthRef.current = nextWidth;
      setLiveWidth(nextWidth);
    };

    const onPointerUp = (upEvent: PointerEvent) => {
      upEvent.stopPropagation();
      upEvent.preventDefault();
      document.removeEventListener("pointermove", onPointerMove);
      document.removeEventListener("pointerup", onPointerUp, true);
      const finalWidth = liveWidthRef.current;
      liveWidthRef.current = null;
      setLiveWidth(null);
      if (didDrag) {
        onAfterResizeDrag?.();
      }
      if (finalWidth != null) {
        queueMicrotask(() => {
          onNodeResizeEnd(finalWidth);
        });
      }
    };

    document.addEventListener("pointermove", onPointerMove);
    document.addEventListener("pointerup", onPointerUp, true);
  };

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
  const dagMetricsGroupHasDiff = shownMetrics.some(
    (m) => m.value != null && m.parentValue != null
  );

  const highlightOpacity =
    data.isHighlighted === false ? ({ opacity: 0.35 } as const) : undefined;

  return (
    <>
      <Handle type="target" position={Position.Top} className="w-2 h-2" />
      <div
        ref={nodeRef}
        className={cn(
          "relative min-w-0 shrink-0 rounded-md border bg-card px-2 py-1.5 shadow-sm cursor-pointer hover-elevate transition-[width,box-shadow]",
          data.isSelected && "ring-2 ring-primary ring-offset-2 ring-offset-background",
          !data.isSelected &&
            data.isSearchFocus &&
            "ring-2 ring-amber-400 ring-offset-2 ring-offset-background"
        )}
        style={{
          width,
          borderLeftColor: data.color,
          borderLeftWidth: "4px",
          ...highlightOpacity,
        }}
        data-testid={`dag-node-${data.id}`}
        aria-selected={data.isSelected === true}
      >
        <div className="flex items-start gap-1.5 mb-0.5 min-w-0">
          {data.selectionMode && data.onSelectionToggle ? (
            <ExperimentSelectionOrderBadge
              experimentId={data.id}
              experimentName={data.label}
              orderNumber={data.selectionOrder ?? null}
              onToggle={data.onSelectionToggle}
            />
          ) : null}
          <div
            className="mt-0.5 h-2 w-2 shrink-0 rounded-full"
            style={{ backgroundColor: data.color }}
          />
          <span className="min-w-0 flex-1 break-words text-xs font-medium leading-snug">
            {data.label}
          </span>
          {getStatusIcon(data.status)}
        </div>

        {data.description ? (
          <p className="mb-0.5 break-words text-[10px] leading-snug text-muted-foreground">
            {data.description}
          </p>
        ) : null}

        {shownMetrics.length > 0 && (
          <div className="mt-1 flex flex-col gap-0 border-t pt-0.5 leading-tight">
            <div className={metricRowGroupTableClass(dagMetricsGroupHasDiff)}>
              {shownMetrics.map((metric) => (
                <MetricNameValueDiffRow
                  key={projectMetricKeyString({
                    name: metric.name,
                    label: metric.label,
                  })}
                  metricName={metric.name}
                  metricLabel={metric.label}
                  value={metric.value}
                  parentValue={metric.parentValue}
                  direction={metric.direction}
                  metricTable={{
                    scope: "group",
                    groupHasAnyDiff: dagMetricsGroupHasDiff,
                  }}
                  classNameProps={{
                    root: "text-[10px]",
                    nameCluster: cn(DAG_METRIC_ROW_SEPARATOR_CLASS, "overflow-visible"),
                    nameInnerCluster: "mr-0 w-full max-w-full items-start overflow-visible",
                    nameTrigger: "whitespace-normal break-words text-muted-foreground",
                    valueCluster: DAG_METRIC_ROW_SEPARATOR_CLASS,
                    valueText: "text-[10px]",
                    deltaText: "font-mono text-[9px] tabular-nums leading-none",
                    deltaIcon: "w-2.5 h-2.5",
                    tableSlot1: DAG_METRIC_ROW_SEPARATOR_CLASS,
                    tableArrow: DAG_METRIC_ROW_SEPARATOR_CLASS,
                    tableSlot2: DAG_METRIC_ROW_SEPARATOR_CLASS,
                  }}
                />
              ))}
            </div>
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
        <div
          role="button"
          tabIndex={0}
          aria-label={`Resize ${data.label} width`}
          className="nodrag nopan absolute bottom-0 right-0 z-10 flex h-3.5 w-3.5 cursor-ew-resize items-end justify-end rounded-br-md p-0.5 text-muted-foreground/70 hover:text-foreground"
          onPointerDown={handleResizePointerDown}
          data-testid={`dag-node-resize-${data.id}`}
        >
          <svg
            aria-hidden
            viewBox="0 0 8 8"
            className="h-2 w-2 shrink-0"
            fill="currentColor"
          >
            <path d="M8 8H6V6H8V8ZM8 4H6V2H8V4ZM4 8H2V6H4V8Z" />
          </svg>
        </div>
      </div>
      <Handle type="source" position={Position.Bottom} className="w-2 h-2" />
    </>
  );
}

const DAG_SEARCH_FOCUS_ZOOM = 1;

function getDagNodeCenter(
  position: { x: number; y: number },
  width: number,
  height = DAG_NODE_HEIGHT_PX
): { x: number; y: number } {
  return {
    x: position.x + width / 2,
    y: position.y + height / 2,
  };
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
  const { fitView, setCenter, getNode } = useReactFlow();
  const savedPositions = useDagLayoutStore(
    (s) => s.layoutsByProject[projectId] ?? EMPTY_DAG_LAYOUT_POSITIONS
  );
  const savedSizes = useDagLayoutStore(
    (s) => s.sizesByProject[projectId] ?? EMPTY_DAG_NODE_SIZES
  );
  const updateNodePosition = useDagLayoutStore((s) => s.updateNodePosition);
  const updateNodeSize = useDagLayoutStore((s) => s.updateNodeSize);
  const replaceProjectLayout = useDagLayoutStore((s) => s.replaceProjectLayout);

  const { selectedExperimentId, setSelectedExperimentId } = useSelectedExperimentStore();
  const [searchQuery, setSearchQuery] = useState("");
  const [searchMatchIndex, setSearchMatchIndex] = useState(0);
  const searchTrimmed = searchQuery.trim().toLowerCase();
  const matchingNodeIds = useMemo(() => {
    if (!searchTrimmed) return [];
    return experiments
      .filter(
        (exp) =>
          exp.name.toLowerCase().includes(searchTrimmed) ||
          (exp.description?.toLowerCase().includes(searchTrimmed) ?? false)
      )
      .map((exp) => exp.id);
  }, [experiments, searchTrimmed]);
  const matchingNodeIdsKey = matchingNodeIds.join(",");
  const {
    selectionMode,
    setSelectionMode,
    orderedIds,
    toggleExperiment,
    getOrderNumber,
  } = useOrderedExperimentSelection();
  /** Node ids currently mid-drag — avoids syncing layout-derived nodes over RF state (error #015). */
  const draggingNodeIdsRef = useRef<Set<string>>(new Set());
  const ignoreNextNodeClickRef = useRef(false);

  const layout = useMemo(
    () => calculateDagTreeLayout(experiments, savedPositions),
    [experiments, savedPositions]
  );

  const focusNodeInViewport = useCallback(
    (nodeId: string) => {
      const run = () => {
        const rfNode = getNode(nodeId);
        const position = rfNode?.position ?? layout.positionsById[nodeId];
        if (!position) return;

        const width = savedSizes[nodeId]?.width ?? DAG_NODE_WIDTH_PX;
        const center = getDagNodeCenter(position, width);
        void setCenter(center.x, center.y, {
          zoom: DAG_SEARCH_FOCUS_ZOOM,
          duration: 300,
        });
      };

      // Wait for React Flow to commit node positions before centering.
      requestAnimationFrame(() => {
        requestAnimationFrame(run);
      });
    },
    [getNode, layout.positionsById, savedSizes, setCenter]
  );

  const focusSearchMatch = useCallback(
    (index: number) => {
      if (matchingNodeIds.length === 0) return;
      const normalized =
        ((index % matchingNodeIds.length) + matchingNodeIds.length) % matchingNodeIds.length;
      setSearchMatchIndex(normalized);
      focusNodeInViewport(matchingNodeIds[normalized]);
    },
    [focusNodeInViewport, matchingNodeIds]
  );

  useEffect(() => {
    setSearchMatchIndex(0);
    if (matchingNodeIds.length === 0) return;
    focusNodeInViewport(matchingNodeIds[0]);
  }, [searchTrimmed, matchingNodeIdsKey, focusNodeInViewport, matchingNodeIds]);

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
      const q = searchTrimmed;
      const matches =
        !q ||
        exp.name.toLowerCase().includes(q) ||
        (exp.description?.toLowerCase().includes(q) ?? false);
      const focusedSearchMatchId = matchingNodeIds[searchMatchIndex];
      map.set(exp.id, {
        id: exp.id,
        label: exp.name,
        description: exp.description || "",
        status: exp.status,
        color: exp.color,
        progress: exp.progress,
        metrics,
        isSelected: selectedExperimentId === exp.id,
        isHighlighted: searchTrimmed ? matches : undefined,
        isSearchFocus: Boolean(searchTrimmed && focusedSearchMatchId === exp.id),
        selectionMode,
        selectionOrder: getOrderNumber(exp.id),
        onSelectionToggle: () => toggleExperiment(exp.id),
        nodeWidth: savedSizes[exp.id]?.width ?? DAG_NODE_WIDTH_PX,
        onNodeResizeEnd: (width) => {
          updateNodeSize(projectId, exp.id, clampDagNodeWidth(width));
        },
        onAfterResizeDrag: () => {
          ignoreNextNodeClickRef.current = true;
        },
      });
    }
    return map;
  }, [
    experiments,
    aggregatedMetricsByExperiment,
    project,
    searchTrimmed,
    matchingNodeIds,
    searchMatchIndex,
    selectedExperimentId,
    selectionMode,
    getOrderNumber,
    toggleExperiment,
    savedSizes,
    projectId,
    updateNodeSize,
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
      if (ignoreNextNodeClickRef.current) {
        ignoreNextNodeClickRef.current = false;
        return;
      }
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
              <div className="flex flex-wrap items-center gap-2 bg-card/95 p-2 rounded-md border shadow-sm">
                <Search className="h-4 w-4 text-muted-foreground shrink-0" />
                <Input
                  placeholder="Search experiments..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="h-8 w-44 sm:w-52 text-sm"
                  data-testid="input-dag-search"
                />
                {searchTrimmed ? (
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
                {searchTrimmed ? (
                  matchingNodeIds.length > 0 ? (
                    <div className="flex items-center gap-0.5">
                      <Button
                        type="button"
                        size="icon"
                        variant="ghost"
                        className="h-6 w-6 shrink-0"
                        onClick={() => focusSearchMatch(searchMatchIndex - 1)}
                        aria-label="Previous search match"
                        data-testid="button-dag-search-prev"
                      >
                        <ChevronLeft className="h-3.5 w-3.5" />
                      </Button>
                      <span
                        className="min-w-10 text-center text-xs tabular-nums text-muted-foreground"
                        data-testid="dag-search-match-count"
                      >
                        {searchMatchIndex + 1}/{matchingNodeIds.length}
                      </span>
                      <Button
                        type="button"
                        size="icon"
                        variant="ghost"
                        className="h-6 w-6 shrink-0"
                        onClick={() => focusSearchMatch(searchMatchIndex + 1)}
                        aria-label="Next search match"
                        data-testid="button-dag-search-next"
                      >
                        <ChevronRight className="h-3.5 w-3.5" />
                      </Button>
                    </div>
                  ) : (
                    <span className="text-xs text-muted-foreground">No matches</span>
                  )
                ) : null}
                <div className="hidden h-6 w-px shrink-0 bg-border sm:block" aria-hidden="true" />
                <CompareLabeledSwitch
                  id="dag-selection-mode"
                  label="Selection mode"
                  checked={selectionMode}
                  onCheckedChange={setSelectionMode}
                  tip="Pick experiments in order; #1 is the compare baseline."
                  ariaLabel="Enable selection mode for compare"
                />
              </div>
            </Panel>
            {selectionMode ? (
              <Panel position="bottom-left" className="m-2">
                <ExperimentCompareBar projectId={projectId} orderedIds={orderedIds} />
              </Panel>
            ) : null}
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
