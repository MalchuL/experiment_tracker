"use client";

import { useMemo, useState } from "react";
import Link from "next/link";
import { PageHeader } from "@/components/shared/page-header";
import { useWorkspaceHeaderActions } from "@/components/shared/workspace-shell";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { EmptyState } from "@/components/shared/empty-state";
import { ListSkeleton } from "@/components/shared/loading-skeleton";
import { useTeams } from "@/domain/teams/hooks";
import { CreateTeamModal } from "@/domain/teams/components";
import { FRONTEND_ROUTES } from "@/lib/constants/frontend-routes";
import { Plus, Users } from "lucide-react";

export default function TeamsPage() {
  const [createOpen, setCreateOpen] = useState(false);
  const { data, isLoading, error, refetch } = useTeams();

  const teams = data ?? [];

  const headerActions = useMemo(() => {
    if (isLoading || error) return null;
    return (
      <Button onClick={() => setCreateOpen(true)} data-testid="button-teams-new-team">
        <Plus className="mr-2 h-4 w-4" />
        New team
      </Button>
    );
  }, [isLoading, error]);

  useWorkspaceHeaderActions(headerActions);

  if (isLoading) {
    return (
      <div className="container mx-auto max-w-screen-2xl space-y-6 p-6">
        <PageHeader title="Teams" description="Organize projects and access" />
        <ListSkeleton />
      </div>
    );
  }

  if (error) {
    return (
      <div className="container mx-auto max-w-screen-2xl space-y-6 p-6">
        <PageHeader title="Teams" description="Organize projects and access" />
        <EmptyState
          icon={Users}
          title="Error loading teams"
          description="Try again later."
          action={<Button onClick={() => refetch()}>Retry</Button>}
        />
      </div>
    );
  }

  return (
    <div className="container mx-auto max-w-screen-2xl space-y-6 p-6">
      <CreateTeamModal open={createOpen} onOpenChange={setCreateOpen} />
      <PageHeader
        title="Teams"
        description="Groups with shared projects and permissions (similar to GitLab groups)"
      />

      {teams.length === 0 ? (
        <EmptyState
          icon={Users}
          title="No teams yet"
          description="Create a team to group projects and manage access in one place."
          action={
            <Button onClick={() => setCreateOpen(true)} data-testid="button-teams-empty-create">
              <Plus className="mr-2 h-4 w-4" />
              New team
            </Button>
          }
        />
      ) : (
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {teams.map((team) => (
            <Link key={team.id} href={FRONTEND_ROUTES.TEAM_BY_ID(team.id)}>
              <Card className="h-full transition-colors hover:bg-muted/40">
                <CardHeader>
                  <CardTitle className="text-lg">{team.name}</CardTitle>
                  <CardDescription className="line-clamp-2">
                    {team.description || "No description"}
                  </CardDescription>
                </CardHeader>
                <CardContent className="text-xs text-muted-foreground">
                  {team.canCreateProject ? "You can create projects here" : "View access"}
                </CardContent>
              </Card>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}
