import { useQuery } from "@tanstack/react-query";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { useExperimentStore } from "@/stores/experiment-store";
import { FlaskConical, Lightbulb, FolderKanban } from "lucide-react";
import type { Project } from "@shared/schema";

export function ProjectSelector() {
  const {
    selectedProjectId,
    isProjectSelectorOpen,
    setSelectedProjectId,
    closeProjectSelector,
  } = useExperimentStore();

  const { data: projects, isLoading } = useQuery<Project[]>({
    queryKey: ["/api/projects"],
  });

  const handleSelectProject = (projectId: string | null) => {
    setSelectedProjectId(projectId);
    closeProjectSelector();
  };

  return (
    <Dialog open={isProjectSelectorOpen} onOpenChange={closeProjectSelector}>
      <DialogContent className="max-w-2xl max-h-[80vh] overflow-auto">
        <DialogHeader>
          <DialogTitle>Select Project</DialogTitle>
          <DialogDescription>
            Choose a project to view its experiments, hypotheses, and visualizations.
          </DialogDescription>
        </DialogHeader>
        
        <div className="space-y-3 mt-4">
          <Button
            variant={selectedProjectId === null ? "default" : "outline"}
            className="w-full justify-start gap-2"
            onClick={() => handleSelectProject(null)}
            data-testid="button-clear-project"
          >
            <FolderKanban className="w-4 h-4" />
            All Projects (Dashboard View)
          </Button>

          {isLoading ? (
            <div className="text-center py-4 text-muted-foreground">Loading projects...</div>
          ) : projects && projects.length > 0 ? (
            projects.map((project) => (
              <Card
                key={project.id}
                className={`cursor-pointer hover-elevate active-elevate-2 ${
                  selectedProjectId === project.id ? "border-primary" : ""
                }`}
                onClick={() => handleSelectProject(project.id)}
                data-testid={`project-card-${project.id}`}
              >
                <CardContent className="p-4">
                  <div className="flex items-start justify-between gap-4">
                    <div className="flex-1 min-w-0">
                      <h3 className="font-medium truncate">{project.name}</h3>
                      <p className="text-sm text-muted-foreground mt-1 line-clamp-2">
                        {project.description || "No description"}
                      </p>
                    </div>
                    <div className="flex flex-col gap-1 text-right">
                      <div className="flex items-center gap-1 text-xs text-muted-foreground">
                        <FlaskConical className="w-3 h-3" />
                        {project.experimentCount}
                      </div>
                      <div className="flex items-center gap-1 text-xs text-muted-foreground">
                        <Lightbulb className="w-3 h-3" />
                        {project.hypothesisCount}
                      </div>
                    </div>
                  </div>
                  {project.metrics.length > 0 && (
                    <div className="flex flex-wrap gap-1 mt-2">
                      {project.metrics.slice(0, 4).map((metric) => (
                        <Badge key={metric.name} variant="secondary" className="text-xs">
                          {metric.name}
                        </Badge>
                      ))}
                      {project.metrics.length > 4 && (
                        <Badge variant="outline" className="text-xs">
                          +{project.metrics.length - 4} more
                        </Badge>
                      )}
                    </div>
                  )}
                </CardContent>
              </Card>
            ))
          ) : (
            <div className="text-center py-4 text-muted-foreground">
              No projects found. Create a project first.
            </div>
          )}
        </div>
      </DialogContent>
    </Dialog>
  );
}
