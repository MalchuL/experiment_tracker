"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
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
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import {
  useInviteProjectMember,
  useLookupProjectUser,
  useProjectMembers,
  useRemoveProjectMember,
  useUpdateProjectMemberRole,
} from "@/domain/projects/hooks";
import type { ProjectMemberRole, ProjectMemberRow } from "@/domain/projects/types/members";
import { useToast } from "@/lib/hooks/use-toast";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "@/components/ui/tooltip";

const ROLE_OPTIONS: { value: ProjectMemberRole; label: string }[] = [
  { value: "admin", label: "Maintainer" },
  { value: "member", label: "Developer" },
  { value: "viewer", label: "Guest" },
];

function initials(row: ProjectMemberRow) {
  const n = row.displayName || row.email || "?";
  return n
    .split(/\s+/)
    .map((p) => p[0])
    .join("")
    .toUpperCase()
    .slice(0, 2);
}

interface ProjectMembersPanelProps {
  projectId: string;
}

export function ProjectMembersPanel({ projectId }: ProjectMembersPanelProps) {
  const { toast } = useToast();
  const { data: members, isLoading, refetch } = useProjectMembers(projectId);
  const invite = useInviteProjectMember(projectId);
  const updateRole = useUpdateProjectMemberRole(projectId);
  const remove = useRemoveProjectMember(projectId);
  const lookup = useLookupProjectUser(projectId);

  const [email, setEmail] = useState("");
  const [resolvedId, setResolvedId] = useState<string | null>(null);
  const [inviteRole, setInviteRole] = useState<ProjectMemberRole>("member");

  const rows = members ?? [];

  const onLookup = () => {
    setResolvedId(null);
    lookup.mutate(email.trim(), {
      onSuccess: (u) => {
        setResolvedId(u.id);
        toast({ title: "User found", description: u.email ?? u.id });
      },
      onError: () => toast({ title: "User not found", variant: "destructive" }),
    });
  };

  const onInvite = () => {
    if (!resolvedId) return;
    invite.mutate(
      { email: email.trim(), role: inviteRole },
      {
        onSuccess: () => {
          setEmail("");
          setResolvedId(null);
          void refetch();
          toast({ title: "Access granted" });
        },
        onError: () => toast({ title: "Invite failed", variant: "destructive" }),
      },
    );
  };

  const onRoleChange = (row: ProjectMemberRow, role: ProjectMemberRole) => {
    if (row.role === "owner") return;
    updateRole.mutate(
      { userId: row.userId, role },
      {
        onSuccess: () => {
          void refetch();
          toast({ title: "Role updated" });
        },
        onError: () => toast({ title: "Update failed", variant: "destructive" }),
      },
    );
  };

  const onRemove = (row: ProjectMemberRow) => {
    remove.mutate(row.userId, {
      onSuccess: () => {
        void refetch();
        toast({ title: "Removed" });
      },
      onError: () => toast({ title: "Remove failed", variant: "destructive" }),
    });
  };

  if (isLoading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Members</CardTitle>
          <CardDescription>Loading…</CardDescription>
        </CardHeader>
      </Card>
    );
  }

  return (
    <TooltipProvider>
      <Card>
        <CardHeader>
          <CardTitle>Members</CardTitle>
          <CardDescription>
            Team members inherit the team role on this project. Maintainers can set a per-project override (role and permissions) for any member; Remove clears the override and restores team inheritance. Invited users who are not on the team get direct access only.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          <div className="flex flex-col gap-3 md:flex-row md:items-end">
            <div className="flex-1 space-y-2">
              <label className="text-sm font-medium">Invite by email</label>
              <Input
                placeholder="user@example.com"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
              />
            </div>
            <div className="w-full md:w-44 space-y-2">
              <label className="text-sm font-medium">Role</label>
              <Select
                value={inviteRole}
                onValueChange={(v) => setInviteRole(v as ProjectMemberRole)}
              >
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
            <Button type="button" variant="secondary" onClick={onLookup} disabled={lookup.isPending}>
              Find user
            </Button>
            <Button type="button" onClick={onInvite} disabled={!resolvedId || invite.isPending}>
              Add to project
            </Button>
          </div>

          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>User</TableHead>
                <TableHead>Source</TableHead>
                <TableHead>Role</TableHead>
                <TableHead className="w-[80px]" />
              </TableRow>
            </TableHeader>
            <TableBody>
              {rows.map((row) => (
                <TableRow key={row.userId}>
                  <TableCell>
                    <div className="flex items-center gap-3">
                      <Avatar className="h-8 w-8">
                        <AvatarFallback className="text-xs">{initials(row)}</AvatarFallback>
                      </Avatar>
                      <div>
                        <div className="font-medium text-sm">
                          {row.displayName || row.email || row.userId}
                        </div>
                        <div className="text-xs text-muted-foreground">{row.email}</div>
                      </div>
                    </div>
                  </TableCell>
                  <TableCell>
                    <Badge
                      variant={
                        row.accessSource === "team" ? "secondary" : "default"
                      }
                    >
                      {row.accessSource === "team"
                        ? "Team"
                        : row.accessSource === "override"
                          ? "Override"
                          : "Direct"}
                    </Badge>
                  </TableCell>
                  <TableCell>
                    {row.role === "owner" ? (
                      <Badge variant="outline">Owner</Badge>
                    ) : (
                      <Tooltip>
                        <TooltipTrigger asChild>
                          <div>
                            <Select
                              value={row.role}
                              disabled={!row.canEdit}
                              onValueChange={(v) => onRoleChange(row, v as ProjectMemberRole)}
                            >
                              <SelectTrigger className="w-[150px]">
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
                        </TooltipTrigger>
                        {!row.canEdit && (
                          <TooltipContent>
                            You cannot change this role
                          </TooltipContent>
                        )}
                      </Tooltip>
                    )}
                  </TableCell>
                  <TableCell>
                    <Tooltip>
                      <TooltipTrigger asChild>
                        <span>
                          <Button
                            type="button"
                            variant="ghost"
                            size="sm"
                            disabled={!row.canRemove}
                            onClick={() => onRemove(row)}
                          >
                            Remove
                          </Button>
                        </span>
                      </TooltipTrigger>
                      {!row.canRemove && (
                        <TooltipContent>
                          {row.accessSource === "team"
                            ? "No project override to clear—change team membership on the team page"
                            : "Cannot remove this user"}
                        </TooltipContent>
                      )}
                    </Tooltip>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </CardContent>
      </Card>
    </TooltipProvider>
  );
}
