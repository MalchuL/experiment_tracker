import { useQuery } from "@tanstack/react-query";
import { Link } from "wouter";
import { PageHeader } from "@/components/page-header";
import { StatusBadge } from "@/components/status-badge";
import { ListSkeleton } from "@/components/loading-skeleton";
import { EmptyState } from "@/components/empty-state";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { FlaskConical, Plus, GitBranch, ArrowRight } from "lucide-react";
import { useState, useMemo } from "react";
import type { Experiment, Project } from "@shared/schema";

interface DAGNode {
  experiment: Experiment;
  children: DAGNode[];
  depth: number;
}

export default function DAGView() {
  const [selectedProjectId, setSelectedProjectId] = useState<string>("all");

  const { data: experiments, isLoading: experimentsLoading } = useQuery<Experiment[]>({
    queryKey: ["/api/experiments"],
  });

  const { data: projects } = useQuery<Project[]>({
    queryKey: ["/api/projects"],
  });

  const filteredExperiments = useMemo(() => {
    if (!experiments) return [];
    if (selectedProjectId === "all") return experiments;
    return experiments.filter(e => e.projectId === selectedProjectId);
  }, [experiments, selectedProjectId]);

  const dagStructure = useMemo(() => {
    if (!filteredExperiments.length) return [];

    const experimentMap = new Map(filteredExperiments.map(e => [e.id, e]));
    const rootExperiments: DAGNode[] = [];
    const childrenMap = new Map<string, Experiment[]>();

    filteredExperiments.forEach(exp => {
      if (exp.parentExperimentId) {
        const children = childrenMap.get(exp.parentExperimentId) || [];
        children.push(exp);
        childrenMap.set(exp.parentExperimentId, children);
      }
    });

    const buildTree = (experiment: Experiment, depth: number): DAGNode => {
      const children = childrenMap.get(experiment.id) || [];
      return {
        experiment,
        depth,
        children: children.map(child => buildTree(child, depth + 1)),
      };
    };

    filteredExperiments.forEach(exp => {
      if (!exp.parentExperimentId || !experimentMap.has(exp.parentExperimentId)) {
        rootExperiments.push(buildTree(exp, 0));
      }
    });

    return rootExperiments;
  }, [filteredExperiments]);

  const renderNode = (node: DAGNode) => {
    const { experiment, children, depth } = node;

    return (
      <div key={experiment.id} className="relative">
        <div 
          className="flex items-start gap-4"
          style={{ marginLeft: `${depth * 2}rem` }}
        >
          {depth > 0 && (
            <div className="absolute left-0 top-1/2 -translate-y-1/2 flex items-center">
              <div 
                className="h-px bg-border"
                style={{ width: `${depth * 2 - 0.5}rem` }}
              />
              <ArrowRight className="w-3 h-3 text-muted-foreground -ml-1" />
            </div>
          )}
          <Link href={`/experiments/${experiment.id}`}>
            <Card 
              className="hover-elevate active-elevate-2 cursor-pointer w-72"
              data-testid={`dag-node-${experiment.id}`}
            >
              <CardContent className="p-3">
                <div className="flex items-start gap-3">
                  <div className="flex items-center justify-center w-8 h-8 rounded-md bg-accent flex-shrink-0">
                    <FlaskConical className="w-4 h-4 text-accent-foreground" />
                  </div>
                  <div className="min-w-0 flex-1">
                    <p className="text-sm font-medium truncate">{experiment.name}</p>
                    <p className="text-xs text-muted-foreground font-mono">
                      {experiment.id.slice(0, 8)}
                    </p>
                  </div>
                </div>
                <div className="flex items-center justify-between mt-2">
                  <StatusBadge status={experiment.status} size="sm" />
                  {children.length > 0 && (
                    <Badge variant="outline" className="text-xs">
                      {children.length} child{children.length !== 1 ? "ren" : ""}
                    </Badge>
                  )}
                </div>
              </CardContent>
            </Card>
          </Link>
        </div>
        {children.length > 0 && (
          <div className="mt-3 space-y-3">
            {children.map(child => renderNode(child))}
          </div>
        )}
      </div>
    );
  };

  if (experimentsLoading) {
    return (
      <div className="space-y-6">
        <PageHeader 
          title="DAG View" 
          description="Visualize experiment hierarchy as a directed acyclic graph" 
        />
        <ListSkeleton count={3} />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <PageHeader
        title="DAG View"
        description="Visualize experiment hierarchy as a directed acyclic graph"
        actions={
          <div className="flex items-center gap-2">
            <Select value={selectedProjectId} onValueChange={setSelectedProjectId}>
              <SelectTrigger className="w-48" data-testid="select-project-filter">
                <SelectValue placeholder="Filter by project" />
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
            <Link href="/experiments">
              <Button data-testid="button-new-experiment">
                <Plus className="w-4 h-4 mr-2" />
                New Experiment
              </Button>
            </Link>
          </div>
        }
      />

      {!experiments || experiments.length === 0 ? (
        <EmptyState
          icon={GitBranch}
          title="No experiments yet"
          description="Create experiments to see their relationships in the DAG view."
          action={
            <Link href="/experiments">
              <Button>
                <Plus className="w-4 h-4 mr-2" />
                Create Experiment
              </Button>
            </Link>
          }
        />
      ) : dagStructure.length === 0 ? (
        <EmptyState
          icon={GitBranch}
          title="No experiments in this project"
          description="Select a different project or create new experiments."
        />
      ) : (
        <Card>
          <CardHeader>
            <CardTitle className="text-base flex items-center gap-2">
              <GitBranch className="w-4 h-4" />
              Experiment Hierarchy
            </CardTitle>
          </CardHeader>
          <CardContent className="overflow-x-auto">
            <div className="space-y-4 min-w-max pb-4">
              {dagStructure.map(node => renderNode(node))}
            </div>
          </CardContent>
        </Card>
      )}

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Legend</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex flex-wrap gap-4">
            <div className="flex items-center gap-2">
              <div className="w-3 h-3 rounded-full bg-muted" />
              <span className="text-sm text-muted-foreground">Planned</span>
            </div>
            <div className="flex items-center gap-2">
              <div className="w-3 h-3 rounded-full bg-blue-500" />
              <span className="text-sm text-muted-foreground">Running</span>
            </div>
            <div className="flex items-center gap-2">
              <div className="w-3 h-3 rounded-full bg-green-500" />
              <span className="text-sm text-muted-foreground">Complete</span>
            </div>
            <div className="flex items-center gap-2">
              <div className="w-3 h-3 rounded-full bg-red-500" />
              <span className="text-sm text-muted-foreground">Failed</span>
            </div>
            <div className="flex items-center gap-2">
              <ArrowRight className="w-4 h-4 text-muted-foreground" />
              <span className="text-sm text-muted-foreground">Parent → Child relationship</span>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
