import { Card, CardContent } from "@/components/ui/card";
import { Play, CheckCircle2, XCircle } from "lucide-react";
import type { DashboardStats } from "../types";

interface ExperimentStatusCardsProps {
  stats: DashboardStats | undefined;
}

export function ExperimentStatusCards({ stats }: ExperimentStatusCardsProps) {
  return (
    <div className="grid gap-4 md:grid-cols-3">
      <Card className="hover-elevate">
        <CardContent className="p-4">
          <div className="flex items-center gap-3">
            <div className="flex size-10 shrink-0 items-center justify-center rounded-full bg-blue-500/15">
              <Play className="size-5 shrink-0 text-blue-600 dark:text-blue-400" aria-hidden />
            </div>
            <div>
              <p className="text-2xl font-bold">
                {stats?.runningExperiments ?? 0}
              </p>
              <p className="text-sm text-muted-foreground">Running</p>
            </div>
          </div>
        </CardContent>
      </Card>
      <Card className="hover-elevate">
        <CardContent className="p-4">
          <div className="flex items-center gap-3">
            <div className="flex size-10 shrink-0 items-center justify-center rounded-full bg-green-500/15">
              <CheckCircle2 className="size-5 shrink-0 text-green-600 dark:text-green-400" aria-hidden />
            </div>
            <div>
              <p className="text-2xl font-bold">
                {stats?.completedExperiments ?? 0}
              </p>
              <p className="text-sm text-muted-foreground">Completed</p>
            </div>
          </div>
        </CardContent>
      </Card>
      <Card className="hover-elevate">
        <CardContent className="p-4">
          <div className="flex items-center gap-3">
            <div className="flex size-10 shrink-0 items-center justify-center rounded-full bg-red-500/15">
              <XCircle className="size-5 shrink-0 text-red-600 dark:text-red-400" aria-hidden />
            </div>
            <div>
              <p className="text-2xl font-bold">
                {stats?.failedExperiments ?? 0}
              </p>
              <p className="text-sm text-muted-foreground">Failed</p>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}


