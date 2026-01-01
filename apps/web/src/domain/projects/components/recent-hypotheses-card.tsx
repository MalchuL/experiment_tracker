import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { StatusBadge } from "@/components/shared/status-badge";
import { Lightbulb } from "lucide-react";
import Link from "next/link";
import type { Hypothesis } from "@/domain/hypothesis/types/types";

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
                  <div className="flex items-center gap-3 min-w-0">
                    <div className="flex items-center justify-center w-8 h-8 rounded-md bg-accent">
                      <Lightbulb className="w-4 h-4 text-accent-foreground" />
                    </div>
                    <p className="text-sm font-medium truncate">
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

