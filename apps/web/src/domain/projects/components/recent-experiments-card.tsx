import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { StatusBadge } from "@/components/shared/status-badge";
import { FlaskConical } from "lucide-react";
import Link from "next/link";
import type { Experiment } from "@/domain/experiments/types";

interface RecentExperimentsCardProps {
  experiments: Experiment[] | undefined;
}

export function RecentExperimentsCard({
  experiments,
}: RecentExperimentsCardProps) {
  return (
    <Card className="lg:col-span-4">
      <CardHeader className="flex flex-row items-center justify-between gap-2">
        <CardTitle className="text-lg font-medium">Recent Experiments</CardTitle>
        <Link href="/experiments">
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
              <Link key={experiment.id} href={`/experiments/${experiment.id}`}>
                <div
                  className="flex items-center justify-between gap-4 p-3 rounded-md hover-elevate active-elevate-2 cursor-pointer"
                  data-testid={`experiment-row-${experiment.id}`}
                >
                  <div className="flex items-center gap-3 min-w-0">
                    <div className="flex items-center justify-center w-8 h-8 rounded-md bg-accent">
                      <FlaskConical className="w-4 h-4 text-accent-foreground" />
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


