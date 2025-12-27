import { useCallback, useMemo, useEffect } from "react";
import { useQuery, useMutation } from "@tanstack/react-query";
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
  Panel,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import { PageHeader } from "@/components/page-header";
import { ListSkeleton } from "@/components/loading-skeleton";
import { EmptyState } from "@/components/empty-state";
import { ExperimentSidebar } from "@/components/experiment-sidebar";
import { Card, CardTitle } from "@/components/ui/card";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { useExperimentStore } from "@/stores/experiment-store";
import { queryClient, apiRequest } from "@/lib/queryClient";
import { useToast } from "@/hooks/use-toast";
import { GitBranch, Clock, Play, CheckCircle2, XCircle } from "lucide-react";
import type { Experiment, Project } from "@shared/schema";

interface ExperimentNodeData {
  id: string;
  label: string;
  status: string;
  color: string;
  progress: number;
}

function ExperimentNode({ data }: { data: ExperimentNodeData }) {
  const getStatusIcon = (status: string) => {
    switch (status) {
      case "running":
        return <Play className="w-3 h-3" />;
      case "complete":
        return <CheckCircle2 className="w-3 h-3" />;
      case "failed":
        return <XCircle className="w-3 h-3" />;
      default:
        return <Clock className="w-3 h-3" />;
    }
  };

  return (
    <>
      <Handle type="target" position={Position.Top} className="w-2 h-2" />
      <div
        className="px-3 py-2 rounded-md border bg-card shadow-sm cursor-pointer hover-elevate min-w-[160px]"
        style={{ borderLeftColor: data.color, borderLeftWidth: "4px" }}
        data-testid={`dag-node-${data.id}`}
      >
        <div className="flex items-center gap-2 mb-1">
          <div
            className="w-2 h-2 rounded-full"
            style={{ backgroundColor: data.color }}
          />
          <span className="text-sm font-medium truncate">{data.label}</span>
        </div>
        <div className="flex items-center justify-between">
          <span className="text-xs text-muted-foreground font-mono">
            {data.id.slice(0, 8)}
          </span>
          <div className="flex items-center gap-1">
            {getStatusIcon(data.status)}
            <span className="text-xs capitalize">{data.status}</span>
          </div>
        </div>
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
  const { toast } = useToast();
  const {
    selectedExperimentId,
    selectedProjectId,
    setSelectedExperimentId,
    setSelectedProjectId,
  } = useExperimentStore();

  const { data: projects } = useQuery<Project[]>({
    queryKey: ["/api/projects"],
  });

  const { data: experiments, isLoading: experimentsLoading } = useQuery<Experiment[]>({
    queryKey: selectedProjectId
      ? ["/api/projects", selectedProjectId, "experiments"]
      : ["/api/experiments"],
    enabled: true,
  });

  const { data: aggregatedMetrics } = useQuery<Record<string, Record<string, number | null>>>({
    queryKey: ["/api/projects", selectedProjectId, "metrics"],
    enabled: !!selectedProjectId,
  });

  const selectedProject = projects?.find((p) => p.id === selectedProjectId);

  const updateParentMutation = useMutation({
    mutationFn: async ({
      experimentId,
      parentId,
    }: {
      experimentId: string;
      parentId: string | null;
    }) => {
      return apiRequest("PATCH", `/api/experiments/${experimentId}`, {
        parentExperimentId: parentId,
      });
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["/api/experiments"] });
      queryClient.invalidateQueries({
        queryKey: ["/api/projects", selectedProjectId, "experiments"],
      });
      toast({
        title: "Parent updated",
        description: "Experiment hierarchy has been updated.",
      });
    },
    onError: () => {
      toast({
        title: "Error",
        description: "Failed to update parent.",
        variant: "destructive",
      });
    },
  });

  const filteredExperiments = useMemo(() => {
    if (!experiments) return [];
    if (!selectedProjectId) return experiments;
    return experiments.filter((e) => e.projectId === selectedProjectId);
  }, [experiments, selectedProjectId]);

  const { initialNodes, initialEdges } = useMemo(() => {
    if (!filteredExperiments.length) return { initialNodes: [], initialEdges: [] };

    const experimentMap = new Map(filteredExperiments.map((e) => [e.id, e]));
    const depths = new Map<string, number>();
    const columns = new Map<number, string[]>();

    const calculateDepth = (exp: Experiment, visited: Set<string> = new Set()): number => {
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

    filteredExperiments.forEach((exp) => calculateDepth(exp));

    filteredExperiments.forEach((exp) => {
      const depth = depths.get(exp.id) || 0;
      if (!columns.has(depth)) columns.set(depth, []);
      columns.get(depth)!.push(exp.id);
    });

    const nodes: Node<ExperimentNodeData>[] = filteredExperiments.map((exp) => {
      const depth = depths.get(exp.id) || 0;
      const columnExps = columns.get(depth) || [];
      const indexInColumn = columnExps.indexOf(exp.id);
      const columnWidth = columnExps.length;

      return {
        id: exp.id,
        type: "experiment",
        position: {
          x: (indexInColumn - (columnWidth - 1) / 2) * 220,
          y: depth * 120,
        },
        data: {
          id: exp.id,
          label: exp.name,
          status: exp.status,
          color: exp.color,
          progress: exp.progress,
        },
      };
    });

    const edges: Edge[] = filteredExperiments
      .filter((exp) => exp.parentExperimentId && experimentMap.has(exp.parentExperimentId))
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
  }, [filteredExperiments]);

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

  if (experimentsLoading) {
    return (
      <div className="space-y-6">
        <PageHeader
          title="DAG View"
          description="Visualize experiment hierarchy with React Flow"
        />
        <ListSkeleton count={3} />
      </div>
    );
  }

  return (
    <div className="h-[calc(100vh-8rem)] flex flex-col">
      <PageHeader
        title="DAG View"
        description="Visualize experiment hierarchy as a directed acyclic graph"
        actions={
          <div className="flex items-center gap-2">
            <Select
              value={selectedProjectId || "all"}
              onValueChange={(v) => setSelectedProjectId(v === "all" ? null : v)}
            >
              <SelectTrigger className="w-48" data-testid="select-project-filter">
                <SelectValue placeholder="All Projects" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Projects</SelectItem>
                {projects?.map((project) => (
                  <SelectItem key={project.id} value={project.id}>
                    {project.name}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        }
      />

      {filteredExperiments.length === 0 ? (
        <EmptyState
          icon={GitBranch}
          title="No experiments yet"
          description={
            selectedProjectId
              ? "No experiments in this project. Create experiments to see their relationships."
              : "Create experiments to see their relationships in the DAG view."
          }
        />
      ) : (
        <Card className="flex-1 overflow-hidden">
          <ReactFlow
            nodes={nodes}
            edges={edges}
            onNodesChange={onNodesChange}
            onEdgesChange={onEdgesChange}
            onNodeClick={onNodeClick}
            nodeTypes={nodeTypes}
            fitView
            fitViewOptions={{ padding: 0.2 }}
            minZoom={0.3}
            maxZoom={1.5}
            proOptions={{ hideAttribution: true }}
          >
            <Controls />
            <Background gap={16} />
            <Panel position="bottom-left">
              <Card className="p-3">
                <CardTitle className="text-xs mb-2">Legend</CardTitle>
                <div className="flex flex-wrap gap-3 text-xs">
                  <div className="flex items-center gap-1">
                    <Clock className="w-3 h-3" />
                    <span>Planned</span>
                  </div>
                  <div className="flex items-center gap-1">
                    <Play className="w-3 h-3 text-blue-500" />
                    <span>Running</span>
                  </div>
                  <div className="flex items-center gap-1">
                    <CheckCircle2 className="w-3 h-3 text-green-500" />
                    <span>Complete</span>
                  </div>
                  <div className="flex items-center gap-1">
                    <XCircle className="w-3 h-3 text-red-500" />
                    <span>Failed</span>
                  </div>
                </div>
              </Card>
            </Panel>
          </ReactFlow>
        </Card>
      )}

      {selectedExperimentId && (
        <ExperimentSidebar
          experimentId={selectedExperimentId}
          onClose={() => setSelectedExperimentId(null)}
          projectMetrics={selectedProject?.metrics}
          aggregatedMetrics={
            aggregatedMetrics?.[selectedExperimentId] || undefined
          }
        />
      )}
    </div>
  );
}
