"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { PageHeader } from "@/components/shared/page-header";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Form,
  FormControl,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from "@/components/ui/form";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Badge } from "@/components/ui/badge";
import {
  useAddTeamMember,
  useRemoveTeamMember,
  useTeam,
  useTeamMembers,
  useUpdateTeam,
  useUpdateTeamMember,
} from "@/domain/teams/hooks";
import { teamsService } from "@/domain/teams/services";
import type { TeamMemberRow, TeamRole } from "@/domain/teams/types";
import { FRONTEND_ROUTES } from "@/lib/constants/frontend-routes";
import { useToast } from "@/lib/hooks/use-toast";
import { ArrowLeft, Trash2 } from "lucide-react";
import { ListSkeleton } from "@/components/shared/loading-skeleton";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";

const settingsSchema = z.object({
  name: z.string().min(1).max(100),
  description: z.string().max(500).optional().default(""),
});

type SettingsForm = z.infer<typeof settingsSchema>;

const ROLE_OPTIONS: { value: TeamRole; label: string; hint: string }[] = [
  { value: "admin", label: "Maintainer", hint: "Manage team and projects" },
  { value: "member", label: "Developer", hint: "Work on projects" },
  { value: "viewer", label: "Guest", hint: "Read-only" },
];

function initials(row: TeamMemberRow) {
  const n = row.displayName || row.email || "?";
  return n
    .split(/\s+/)
    .map((p) => p[0])
    .join("")
    .toUpperCase()
    .slice(0, 2);
}

export default function TeamDetailPage() {
  const params = useParams<{ teamId: string }>();
  const teamId = params.teamId;
  const { toast } = useToast();
  const { data: team, isLoading: teamLoading, refetch: refetchTeam } = useTeam(teamId);
  const { data: members, isLoading: membersLoading, refetch: refetchMembers } =
    useTeamMembers(teamId);
  const updateTeam = useUpdateTeam();
  const addMember = useAddTeamMember(teamId);
  const updateMember = useUpdateTeamMember(teamId);
  const removeMember = useRemoveTeamMember(teamId);

  const [inviteEmail, setInviteEmail] = useState("");
  const [inviteUserId, setInviteUserId] = useState<string | null>(null);
  const [inviteRole, setInviteRole] = useState<TeamRole>("member");
  const [lookupPending, setLookupPending] = useState(false);

  const form = useForm<SettingsForm>({
    resolver: zodResolver(settingsSchema as any),
    defaultValues: { name: "", description: "" },
  });

  useEffect(() => {
    if (team) {
      form.reset({ name: team.name, description: team.description ?? "" });
    }
  }, [team, form]);

  const onSaveSettings = useCallback(
    (values: SettingsForm) => {
      if (!teamId) return;
      updateTeam.mutate(
        { id: teamId, name: values.name, description: values.description || null },
        {
          onSuccess: () => {
            void refetchTeam();
            toast({ title: "Team updated" });
          },
          onError: () => toast({ title: "Update failed", variant: "destructive" }),
        },
      );
    },
    [teamId, updateTeam, refetchTeam, toast],
  );

  const onLookup = async () => {
    if (!teamId || !inviteEmail.trim()) return;
    setLookupPending(true);
    setInviteUserId(null);
    try {
      const u = await teamsService.lookupUser(teamId, inviteEmail.trim());
      setInviteUserId(u.id);
      toast({ title: "User found", description: u.email ?? u.id });
    } catch {
      toast({ title: "User not found", variant: "destructive" });
    } finally {
      setLookupPending(false);
    }
  };

  const onInvite = () => {
    if (!teamId || !inviteUserId) return;
    addMember.mutate(
      { userId: inviteUserId, teamId, role: inviteRole },
      {
        onSuccess: () => {
          setInviteEmail("");
          setInviteUserId(null);
          void refetchMembers();
          toast({ title: "Member added" });
        },
        onError: () => toast({ title: "Could not add member", variant: "destructive" }),
      },
    );
  };

  const onRoleChange = (row: TeamMemberRow, role: TeamRole) => {
    if (!teamId || row.isTeamOwner) return;
    updateMember.mutate(
      { userId: row.userId, teamId, role },
      {
        onSuccess: () => {
          void refetchMembers();
          toast({ title: "Role updated" });
        },
        onError: () => toast({ title: "Could not update role", variant: "destructive" }),
      },
    );
  };

  const onRemove = (row: TeamMemberRow) => {
    if (!teamId || row.isTeamOwner) return;
    removeMember.mutate(
      { userId: row.userId, teamId },
      {
        onSuccess: () => {
          void refetchMembers();
          toast({ title: "Member removed" });
        },
        onError: () => toast({ title: "Could not remove member", variant: "destructive" }),
      },
    );
  };

  const loading = teamLoading || membersLoading;
  const memberRows = useMemo(() => members ?? [], [members]);

  if (loading && !team) {
    return (
      <div className="container mx-auto max-w-screen-2xl space-y-6 p-6">
        <ListSkeleton />
      </div>
    );
  }

  if (!team) {
    return (
      <div className="container mx-auto max-w-screen-2xl p-6">
        <p className="text-muted-foreground">Team not found or no access.</p>
        <Button asChild variant="ghost" className="mt-2 h-auto px-0 text-primary hover:underline">
          <Link href={FRONTEND_ROUTES.TEAMS}>Back to teams</Link>
        </Button>
      </div>
    );
  }

  return (
    <div className="container mx-auto max-w-screen-2xl space-y-8 p-6">
      <div className="flex items-center gap-3">
        <Button variant="ghost" size="icon" asChild>
          <Link href={FRONTEND_ROUTES.TEAMS} aria-label="Back">
            <ArrowLeft className="h-4 w-4" />
          </Link>
        </Button>
        <PageHeader title={team.name} description="Team settings and members" />
      </div>

      <Card>
        <CardHeader>
          <CardTitle>General</CardTitle>
          <CardDescription>Name and description visible to members.</CardDescription>
        </CardHeader>
        <CardContent>
          <Form {...form}>
            <form onSubmit={form.handleSubmit(onSaveSettings)} className="max-w-xl space-y-4">
              <FormField
                control={form.control}
                name="name"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Name</FormLabel>
                    <FormControl>
                      <Input {...field} />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
              <FormField
                control={form.control}
                name="description"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Description</FormLabel>
                    <FormControl>
                      <Textarea {...field} />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
              <Button type="submit" disabled={updateTeam.isPending}>
                Save changes
              </Button>
            </form>
          </Form>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Members</CardTitle>
          <CardDescription>
            Maintainer / Developer / Guest map to admin, member, and viewer. Owner cannot be removed here.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          <div className="flex flex-col gap-3 md:flex-row md:items-end">
            <div className="flex-1 space-y-2">
              <label className="text-sm font-medium">Invite by email</label>
              <Input
                placeholder="colleague@company.com"
                value={inviteEmail}
                onChange={(e) => setInviteEmail(e.target.value)}
              />
            </div>
            <div className="w-full space-y-2 md:w-48">
              <label className="text-sm font-medium">Role</label>
              <Select value={inviteRole} onValueChange={(v) => setInviteRole(v as TeamRole)}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {ROLE_OPTIONS.map((o) => (
                    <SelectItem key={o.value} value={o.value}>
                      {o.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <Button type="button" variant="secondary" onClick={onLookup} disabled={lookupPending}>
              Find user
            </Button>
            <Button type="button" onClick={onInvite} disabled={!inviteUserId || addMember.isPending}>
              Add member
            </Button>
          </div>

          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>User</TableHead>
                <TableHead>Role</TableHead>
                <TableHead className="w-[100px]" />
              </TableRow>
            </TableHeader>
            <TableBody>
              {memberRows.map((row) => (
                <TableRow key={row.userId}>
                  <TableCell>
                    <div className="flex items-center gap-3">
                      <Avatar className="h-8 w-8">
                        <AvatarFallback className="text-xs">{initials(row)}</AvatarFallback>
                      </Avatar>
                      <div>
                        <div className="text-sm font-medium">
                          {row.displayName || row.email || row.userId}
                        </div>
                        <div className="text-xs text-muted-foreground">{row.email}</div>
                        {row.isTeamOwner && (
                          <Badge variant="secondary" className="mt-1">
                            Owner
                          </Badge>
                        )}
                      </div>
                    </div>
                  </TableCell>
                  <TableCell>
                    <Select
                      value={row.role}
                      disabled={row.isTeamOwner || row.role === "admin"}
                      onValueChange={(v) => onRoleChange(row, v as TeamRole)}
                    >
                      <SelectTrigger className="w-[160px]">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        {ROLE_OPTIONS.map((o) => (
                          <SelectItem key={o.value} value={o.value}>
                            {o.label}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </TableCell>
                  <TableCell>
                    {!row.isTeamOwner && row.role !== "admin" && (
                      <Button
                        type="button"
                        variant="ghost"
                        size="icon"
                        onClick={() => onRemove(row)}
                        aria-label="Remove member"
                      >
                        <Trash2 className="h-4 w-4 text-destructive" />
                      </Button>
                    )}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </CardContent>
      </Card>
    </div>
  );
}
