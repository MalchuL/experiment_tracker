export interface Team {
  id: string;
  name: string;
  description: string | null;
  ownerId: string | null;
  createdAt: string;
}

export interface TeamListItem extends Team {
  canCreateProject: boolean;
}

export type TeamRole = "owner" | "admin" | "member" | "viewer";

export interface TeamMemberRow {
  memberId: string | null;
  userId: string;
  teamId: string;
  role: TeamRole;
  email: string | null;
  displayName: string | null;
  isTeamOwner: boolean;
}

export interface TeamMemberWritePayload {
  userId: string;
  teamId: string;
  role: TeamRole;
}
