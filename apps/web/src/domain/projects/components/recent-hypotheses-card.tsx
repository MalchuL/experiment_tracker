import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { StatusBadge } from "@/components/shared/status-badge";
import { Lightbulb } from "lucide-react";
import Link from "next/link";
import type { Hypothesis } from "@/domain/hypothesis/types";

interface RecentHypothesesCardProps {
  hypotheses: Hypothesis[] | undefined;
}

export function RecentHypothesesCard({
  hypotheses,
}: RecentHypothesesCardProps) {
  return (
    <Card className="lg:col-span-3">
      <CardHeader className="flex flex-row items-center justify-between gap-2">
        <CardTitle className="text-lg font-medium">Hypothesis Status</CardTitle>
        <Link href="/hypotheses">
          <span className="text-sm text-muted-foreground hover:text-foreground transition-colors cursor-pointer">
            View all
          </span>
        </Link>
      </CardHeader>
      <CardContent>
        <div className="space-y-4">
          {!hypotheses || hypotheses.length === 0 ? (
            <p className="text-sm text-muted-foreground text-center py-8">
              No hypotheses yet. Create your first hypothesis to track research
              claims.
            </p>
          ) : (
            hypotheses.slice(0, 5).map((hypothesis) => (
              <Link
                key={hypothesis.id}
                href={`/hypotheses/${hypothesis.id}`}
              >
                <div
                  className="flex items-center justify-between gap-4 p-3 rounded-md hover-elevate active-elevate-2 cursor-pointer"
                  data-testid={`hypothesis-row-${hypothesis.id}`}
                >
                  <div className="flex min-w-0 flex-1 items-center gap-3">
                    <div className="flex size-8 shrink-0 items-center justify-center rounded-md bg-accent">
                      <Lightbulb className="size-4 shrink-0 text-accent-foreground" aria-hidden />
                    </div>
                    <p className="min-w-0 flex-1 truncate text-sm font-medium">
                      {hypothesis.title}
                    </p>
                  </div>
                  <StatusBadge status={hypothesis.status} size="sm" />
                </div>
              </Link>
            ))
          )}
        </div>
      </CardContent>
    </Card>
  );
}


