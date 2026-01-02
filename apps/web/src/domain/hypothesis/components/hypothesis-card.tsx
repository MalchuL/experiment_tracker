"use client";

import { Link } from "wouter";
import { Card, CardContent } from "@/components/ui/card";
import { StatusBadge } from "@/components/shared/status-badge";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Lightbulb, MoreVertical, User, Calendar } from "lucide-react";
import { format } from "date-fns";
import type { Hypothesis } from "@/domain/hypothesis/types";

interface HypothesisCardProps {
  hypothesis: Hypothesis;
  projectId: string;
  projectName?: string;
  onDelete: (hypothesisId: string) => void;
}

export function HypothesisCard({
  hypothesis,
  projectId,
  projectName,
  onDelete,
}: HypothesisCardProps) {
  return (
    <Link href={`/projects/${projectId}/hypotheses/${hypothesis.id}`}>
      <Card
        className="hover-elevate active-elevate-2 cursor-pointer"
        data-testid={`card-hypothesis-${hypothesis.id}`}
      >
        <CardContent className="p-4">
          <div className="flex items-center justify-between gap-4">
            <div className="flex items-center gap-3 min-w-0 flex-1">
              <div className="flex items-center justify-center w-10 h-10 rounded-md bg-accent flex-shrink-0">
                <Lightbulb className="w-5 h-5 text-accent-foreground" />
              </div>
              <div className="min-w-0 flex-1">
                <p className="font-medium truncate">{hypothesis.title}</p>
                <div className="flex items-center gap-3 text-xs text-muted-foreground mt-1 flex-wrap">
                  {projectName && <span>{projectName}</span>}
                  <span className="flex items-center gap-1">
                    <User className="w-3 h-3" />
                    {hypothesis.author}
                  </span>
                  <span className="flex items-center gap-1">
                    <Calendar className="w-3 h-3" />
                    {format(new Date(hypothesis.createdAt), "MMM d")}
                  </span>
                </div>
              </div>
            </div>
            <div className="flex items-center gap-2 flex-shrink-0">
              <StatusBadge status={hypothesis.status} />
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
                      onDelete(hypothesis.id);
                    }}
                    data-testid={`button-delete-hypothesis-${hypothesis.id}`}
                  >
                    Delete
                  </DropdownMenuItem>
                </DropdownMenuContent>
              </DropdownMenu>
            </div>
          </div>
          {hypothesis.description && (
            <p className="text-sm text-muted-foreground mt-3 ml-13 line-clamp-2">
              {hypothesis.description}
            </p>
          )}
        </CardContent>
      </Card>
    </Link>
  );
}

