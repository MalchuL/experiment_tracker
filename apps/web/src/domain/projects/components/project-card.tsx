"use client";

import Link from "next/link";
import { format, parseISO } from "date-fns";
import { Card, CardContent } from "@/components/ui/card";
import { FolderKanban, FlaskConical, /* Lightbulb, */ Calendar } from "lucide-react";
import type { Project } from "@/domain/projects/types";
import { FRONTEND_ROUTES } from "@/lib/constants/frontend-routes";

interface ProjectCardProps {
  project: Project;
}

export function ProjectCard({ project }: ProjectCardProps) {
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
                <p className="text-xs text-muted-foreground">
                  {project.owner?.displayName ?? project.owner?.email ?? "No owner"}
                </p>
              </div>
            </div>
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
            {/* <div className="flex items-center gap-1">
              <Lightbulb className="w-3 h-3" />
              <span>{project.hypothesisCount} hypotheses</span>
            </div> */}
          </div>

          <div className="flex items-center gap-1 text-xs text-muted-foreground mt-3 pt-3 border-t">
            <Calendar className="w-3 h-3" />
            <span>Created {format(parseISO(project.createdAt), "MMM d, yyyy")}</span>
          </div>
        </CardContent>
      </Card>
    </Link>
  );
}
