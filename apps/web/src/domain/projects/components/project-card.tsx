"use client";

import Link from "next/link";
import { format } from "date-fns";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { FolderKanban, FlaskConical, Lightbulb, MoreVertical, Calendar } from "lucide-react";
import type { Project } from "@/domain/projects/types";
import { FRONTEND_ROUTES } from "@/lib/constants/frontend-routes";

interface ProjectCardProps {
  project: Project;
  onDelete: (id: string) => void;
}

export function ProjectCard({ project, onDelete }: ProjectCardProps) {
  console.log(project);
  return (
    <Link href={FRONTEND_ROUTES.PROJECT_PAGES.OVERVIEW(project.id)}>
      <Card
        className="hover-elevate active-elevate-2 cursor-pointer h-full"
        data-testid={`card-project-${project.id}`}
      >
        <CardContent className="p-4">
          <div className="flex items-start justify-between gap-2 mb-3">
            <div className="flex items-center gap-3">
              <div className="flex items-center justify-center w-10 h-10 rounded-md bg-primary/10">
                <FolderKanban className="w-5 h-5 text-primary" />
              </div>
              <div className="min-w-0">
                <h3 className="font-medium truncate">{project.name}</h3>
                <p className="text-xs text-muted-foreground">{project.owner.displayName}</p>
              </div>
            </div>
            <DropdownMenu>
              <DropdownMenuTrigger asChild onClick={(e) => e.preventDefault()}>
                <Button variant="ghost" size="icon" className="h-8 w-8">
                  <MoreVertical className="w-4 h-4" />
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end">
                <DropdownMenuItem
                  className="text-destructive"
                  onClick={(e) => {
                    e.preventDefault();
                    onDelete(project.id);
                  }}
                  data-testid={`button-delete-project-${project.id}`}
                >
                  Delete
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
          </div>

          {project.description && (
            <p className="text-sm text-muted-foreground mb-4 line-clamp-2">
              {project.description}
            </p>
          )}

          <div className="flex items-center gap-4 text-xs text-muted-foreground">
            <div className="flex items-center gap-1">
              <FlaskConical className="w-3 h-3" />
              <span>{project.experimentCount} experiments</span>
            </div>
            <div className="flex items-center gap-1">
              <Lightbulb className="w-3 h-3" />
              <span>{project.hypothesisCount} hypotheses</span>
            </div>
          </div>

          <div className="flex items-center gap-1 text-xs text-muted-foreground mt-3 pt-3 border-t">
            <Calendar className="w-3 h-3" />
            <span>Created {format(new Date(project.createdAt), "MMM d, yyyy")}</span>
          </div>
        </CardContent>
      </Card>
    </Link>
  );
}
