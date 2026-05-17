import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { StatusBadge } from "@/components/shared/status-badge";
import { FRONTEND_ROUTES } from "@/lib/constants/frontend-routes";
import { FlaskConical } from "lucide-react";
import Link from "next/link";
import type { Experiment } from "@/domain/experiments/types";

interface RecentExperimentsCardProps {
  experiments: Experiment[] | undefined;
  projectId: string;
}

export function RecentExperimentsCard({
  experiments,
  projectId,
}: RecentExperimentsCardProps) {
  return (
    <Card className="lg:col-span-4">
      <CardHeader className="flex flex-row items-center justify-between gap-2">
        <CardTitle className="text-lg font-medium">Recent Experiments</CardTitle>
        <Link href={FRONTEND_ROUTES.PROJECT_PAGES.EXPERIMENTS(projectId)}>
          <span className="text-sm text-muted-foreground hover:text-foreground transition-colors cursor-pointer">
            View all
          </span>
        </Link>
      </CardHeader>
      <CardContent>
        <div className="space-y-4">
          {!experiments || experiments.length === 0 ? (
            <p className="text-sm text-muted-foreground text-center py-8">
              No experiments yet. Create your first experiment to get started.
            </p>
          ) : (
            experiments.slice(0, 5).map((experiment) => (
              <Link
                key={experiment.id}
                href={FRONTEND_ROUTES.PROJECT_PAGES.EXPERIMENT_DETAILS(
                  experiment.projectId,
                  [experiment.id]
                )}
              >
                <div
                  className="flex items-center justify-between gap-4 p-3 rounded-md hover-elevate active-elevate-2 cursor-pointer"
                  data-testid={`experiment-row-${experiment.id}`}
                >
                  <div className="flex min-w-0 flex-1 items-center gap-3">
                    <div className="flex size-8 shrink-0 items-center justify-center rounded-md bg-accent">
                      <FlaskConical className="size-4 shrink-0 text-accent-foreground" aria-hidden />
                    </div>
                    <div className="min-w-0">
                      <p className="text-sm font-medium truncate">
                        {experiment.name}
                      </p>
                      <p className="text-xs text-muted-foreground font-mono truncate">
                        {experiment.id.slice(0, 8)}
                      </p>
                    </div>
                  </div>
                  <div className="flex items-center gap-2 flex-shrink-0">
                    <StatusBadge status={experiment.status} size="sm" />
                  </div>
                </div>
              </Link>
            ))
          )}
        </div>
      </CardContent>
    </Card>
  );
}


