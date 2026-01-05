"use client";

import { useCallback, useMemo, useEffect } from "react";
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
  MarkerType,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import { PageHeader } from "@/components/shared/page-header";
import { ListSkeleton } from "@/components/shared/loading-skeleton";
import { EmptyState } from "@/components/shared/empty-state";
import { ExperimentSidebar } from "@/components/shared/experiment-sidebar";
import { useCurrentProject } from "@/domain/projects/hooks";
import {
  useExperiments,
  useAggregatedMetrics,
} from "@/domain/experiments/hooks";
import { useSelectedExperimentStore } from "@/domain/experiments/store";
import { Experiment } from "@/domain/experiments/types";
import {
  GitBranch,
  Clock,
  Play,
  CheckCircle2,
  XCircle,
  TrendingUp,
  TrendingDown,
  AlertCircle,
} from "lucide-react";

interface MetricComparison {
  name: string;
  value: number | null;
  parentValue: number | null;
  direction: "maximize" | "minimize";
  isBetter: boolean | null;
}

interface ExperimentNodeData {
  id: string;
  label: string;
  description: string;
  status: string;
  color: string;
  progress: number;
  metrics: MetricComparison[];
  [key: string]: unknown;
}

function ExperimentNode({ data }: { data: ExperimentNodeData }) {
  const getStatusIcon = (status: string) => {
    switch (status) {
      case "running":
        return <Play className="w-3 h-3 text-blue-500" />;
      case "complete":
        return <CheckCircle2 className="w-3 h-3 text-green-500" />;
      case "failed":
        return <XCircle className="w-3 h-3 text-red-500" />;
      default:
        return <Clock className="w-3 h-3" />;
    }
  };

  const formatValue = (v: number | null) => {
    if (v === null) return "NaN";
    return v.toFixed(3);
  };

  return (
    <>
      <Handle type="target" position={Position.Top} className="w-2 h-2" />
      <div
        className="px-3 py-2 rounded-md border bg-card shadow-sm cursor-pointer hover-elevate min-w-[180px]"
        style={{ borderLeftColor: data.color, borderLeftWidth: "4px" }}
        data-testid={`dag-node-${data.id}`}
      >
        <div className="flex items-center gap-2 mb-1">
          <div
            className="w-2 h-2 rounded-full flex-shrink-0"
            style={{ backgroundColor: data.color }}
          />
          <span className="text-sm font-medium truncate flex-1">
            {data.label}
          </span>
          {getStatusIcon(data.status)}
        </div>

        {data.description && (
          <p className="text-xs text-muted-foreground truncate mb-1">
            {data.description}
          </p>
        )}

        {data.metrics.length > 0 && (
          <div className="space-y-0.5 mt-2 border-t pt-1">
            {data.metrics.slice(0, 3).map((metric) => (
              <div
                key={metric.name}
                className="flex items-center justify-between text-xs"
              >
                <span className="text-muted-foreground truncate">
                  {metric.name}
                </span>
                <div className="flex items-center gap-1">
                  <span className="font-mono">{formatValue(metric.value)}</span>
                  {metric.isBetter !== null &&
                    (metric.isBetter ? (
                      <TrendingUp className="w-3 h-3 text-green-500" />
                    ) : (
                      <TrendingDown className="w-3 h-3 text-red-500" />
                    ))}
                </div>
              </div>
            ))}
          </div>
        )}

        {data.status === "running" && (
          <div className="mt-1 h-1 bg-muted rounded-full overflow-hidden">
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

export default function DAGView() {
  const { project, isLoading: projectLoading } = useCurrentProject();
  const projectId = project?.id;
  const { selectedExperimentId, setSelectedExperimentId } =
    useSelectedExperimentStore();
  const { experiments, isLoading: experimentsLoading } =
    useExperiments(projectId);
  const { aggregatedMetrics } = useAggregatedMetrics(projectId);

  // Filter metrics by displayMetrics setting
  const filteredMetrics = useMemo(() => {
    if (!project?.metrics) return [];
    const displayMetrics = project?.settings?.displayMetrics || [];
    if (displayMetrics.length === 0) return project.metrics;
    return project.metrics.filter((m) => displayMetrics.includes(m.name));
  }, [project?.metrics, project?.settings?.displayMetrics]);

  const { initialNodes, initialEdges } = useMemo(() => {
    if (!experiments.length) return { initialNodes: [], initialEdges: [] };

    const experimentMap = new Map(experiments.map((e) => [e.id, e]));
    const depths = new Map<string, number>();
    const columns = new Map<number, string[]>();

    const calculateDepth = (
      exp: Experiment,
      visited: Set<string> = new Set()
    ): number => {
      if (visited.has(exp.id)) return 0;
      if (depths.has(exp.id)) return depths.get(exp.id)!;

      visited.add(exp.id);
      let depth = 0;
      if (exp.parentExperimentId && experimentMap.has(exp.parentExperimentId)) {
        const parent = experimentMap.get(exp.parentExperimentId)!;
        depth = calculateDepth(parent, visited) + 1;
      }
      depths.set(exp.id, depth);
      return depth;
    };

    experiments.forEach((exp) => calculateDepth(exp));

    experiments.forEach((exp) => {
      const depth = depths.get(exp.id) || 0;
      if (!columns.has(depth)) columns.set(depth, []);
      columns.get(depth)!.push(exp.id);
    });

    const displayMetrics = project?.settings?.displayMetrics || [];
    const projectMetrics = project?.metrics || [];

    const nodes: Node<ExperimentNodeData>[] = experiments.map((exp) => {
      const depth = depths.get(exp.id) || 0;
      const columnExps = columns.get(depth) || [];
      const indexInColumn = columnExps.indexOf(exp.id);
      const columnWidth = columnExps.length;

      const expMetrics = aggregatedMetrics?.[exp.id] || {};
      const parentMetrics = exp.parentExperimentId
        ? aggregatedMetrics?.[exp.parentExperimentId] || {}
        : {};

      const metricsToDisplay =
        displayMetrics.length > 0
          ? displayMetrics
          : projectMetrics.slice(0, 2).map((m) => m.name);

      const metrics: MetricComparison[] = metricsToDisplay.map(
        (metricName) => {
          const pm = projectMetrics.find((m) => m.name === metricName);
          const value = expMetrics[metricName] ?? null;
          const parentValue = parentMetrics[metricName] ?? null;
          const direction = pm?.direction || "maximize";

          let isBetter: boolean | null = null;
          if (value !== null && parentValue !== null) {
            if (direction === "maximize") {
              isBetter = value > parentValue;
            } else {
              isBetter = value < parentValue;
            }
          }

          return {
            name: metricName,
            value,
            parentValue,
            direction,
            isBetter,
          };
        }
      );

      return {
        id: exp.id,
        type: "experiment",
        position: {
          x: (indexInColumn - (columnWidth - 1) / 2) * 240,
          y: depth * 160,
        },
        data: {
          id: exp.id,
          label: exp.name,
          description: exp.description || "",
          status: exp.status,
          color: exp.color,
          progress: exp.progress,
          metrics,
        },
      };
    });

    const edges: Edge[] = experiments
      .filter(
        (exp) => exp.parentExperimentId && experimentMap.has(exp.parentExperimentId)
      )
      .map((exp) => ({
        id: `${exp.parentExperimentId}-${exp.id}`,
        source: exp.parentExperimentId!,
        target: exp.id,
        type: "smoothstep",
        animated: exp.status === "running",
        markerEnd: { type: MarkerType.ArrowClosed },
        style: { stroke: exp.color },
      }));

    return { initialNodes: nodes, initialEdges: edges };
  }, [experiments, aggregatedMetrics, project]);

  const [nodes, setNodes, onNodesChange] = useNodesState(initialNodes);
  const [edges, setEdges, onEdgesChange] = useEdgesState(initialEdges);

  useEffect(() => {
    setNodes(initialNodes);
    setEdges(initialEdges);
  }, [initialNodes, initialEdges, setNodes, setEdges]);

  const onNodeClick = useCallback(
    (_: React.MouseEvent, node: Node) => {
      setSelectedExperimentId(node.id);
    },
    [setSelectedExperimentId]
  );

  const isLoading = projectLoading || experimentsLoading;

  if (!projectId) {
    return (
      <div className="flex flex-col items-center justify-center h-[calc(100vh-8rem)] gap-4">
        <AlertCircle className="w-12 h-12 text-muted-foreground" />
        <h2 className="text-lg font-medium">No Project Selected</h2>
        <p className="text-muted-foreground text-center max-w-md">
          Click on the logo in the sidebar to select a project and view its
          experiment DAG.
        </p>
      </div>
    );
  }

  if (isLoading) {
    return (
      <div className="space-y-6">
        <PageHeader
          title="DAG View"
          description="Visualize experiment hierarchy"
        />
        <ListSkeleton count={3} />
      </div>
    );
  }

  return (
    <div className="h-[calc(100vh-8rem)] flex flex-col -m-6">
      <div className="px-6 pt-6 pb-2">
        <PageHeader
          title="DAG View"
          description={`Experiment hierarchy for "${project?.name}"`}
        />
      </div>

      {experiments.length === 0 ? (
        <div className="flex-1 flex items-center justify-center">
          <EmptyState
            icon={GitBranch}
            title="No experiments yet"
            description="Create experiments to see their relationships in the DAG view."
          />
        </div>
      ) : (
        <div className="flex-1">
          <ReactFlow
            nodes={nodes}
            edges={edges}
            onNodesChange={onNodesChange}
            onEdgesChange={onEdgesChange}
            onNodeClick={onNodeClick}
            nodeTypes={nodeTypes}
            fitView
            fitViewOptions={{ padding: 0.1 }}
            minZoom={0.2}
            maxZoom={2}
            proOptions={{ hideAttribution: true }}
          >
            <Controls position="bottom-right" />
            <Background gap={20} />
          </ReactFlow>
        </div>
      )}

      {selectedExperimentId && (
        <ExperimentSidebar
          experimentId={selectedExperimentId}
          onClose={() => setSelectedExperimentId(null)}
          projectMetrics={filteredMetrics}
          aggregatedMetrics={
            aggregatedMetrics?.[selectedExperimentId] || undefined
          }
        />
      )}
    </div>
  );
}

