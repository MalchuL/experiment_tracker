"use client";

import { useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import {
  AlertDialog,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { useDeleteTeam } from "@/domain/teams/hooks/use-teams";
import { FRONTEND_ROUTES } from "@/lib/constants/frontend-routes";
import { QUERY_KEYS } from "@/lib/constants/query-keys";
import { formatDeletionOutcomeDescription } from "@/lib/format-satellite-toast";
import { useToast } from "@/lib/hooks/use-toast";
import { AlertTriangle } from "lucide-react";

export function TeamDangerZone({
  teamId,
  teamName,
  onTeamRefetch,
}: {
  teamId: string;
  teamName: string;
  onTeamRefetch: () => void;
}) {
  const { toast } = useToast();
  const router = useRouter();
  const queryClient = useQueryClient();
  const deleteTeamMutation = useDeleteTeam();

  const [deleteOpen, setDeleteOpen] = useState(false);

  const invalidateTeamQueries = () => {
    void queryClient.invalidateQueries({ queryKey: [QUERY_KEYS.TEAMS.LIST] });
    void queryClient.invalidateQueries({ queryKey: [QUERY_KEYS.TEAMS.GET_BY_ID(teamId)] });
  };

  const handleConfirmRemoveTeam = () => {
    deleteTeamMutation.mutate(teamId, {
      onSuccess: (data) => {
        setDeleteOpen(false);
        invalidateTeamQueries();
        onTeamRefetch();
        toast({
          title: data.success ? "Team removed" : "Team removed (warnings)",
          description: data.success ? "No errors reported." : formatDeletionOutcomeDescription(data),
          variant: data.success ? "default" : "destructive",
        });
        router.push(FRONTEND_ROUTES.TEAMS);
      },
      onError: () => toast({ title: "Failed to delete team", variant: "destructive" }),
    });
  };

  return (
    <>
      <Card className="border-destructive/40 bg-destructive/5">
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-destructive">
            <AlertTriangle className="h-5 w-5" />
            Danger zone
          </CardTitle>
          <CardDescription>
            Removing a team affects access and organization for{" "}
            <span className="font-medium text-foreground">{teamName}</span>. Confirm before deleting.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex flex-wrap gap-2">
            <Button type="button" variant="destructive" onClick={() => setDeleteOpen(true)}>
              Remove team…
            </Button>
          </div>
        </CardContent>
      </Card>

      <AlertDialog open={deleteOpen} onOpenChange={setDeleteOpen}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Remove this team permanently?</AlertDialogTitle>
            <AlertDialogDescription>
              This deletes the team according to server rules. Membership and related data may be
              removed. This cannot be undone.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel disabled={deleteTeamMutation.isPending}>Cancel</AlertDialogCancel>
            <Button
              type="button"
              variant="destructive"
              disabled={deleteTeamMutation.isPending}
              onClick={handleConfirmRemoveTeam}
            >
              {deleteTeamMutation.isPending ? "Removing…" : "Remove team"}
            </Button>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </>
  );
}
