export type ProjectMemberAccessSource = "direct" | "team" | "override";

export type ProjectMemberRole = "owner" | "admin" | "member" | "viewer";

export interface ProjectMemberRow {
  userId: string;
  email: string | null;
  displayName: string | null;
  role: ProjectMemberRole;
  accessSource: ProjectMemberAccessSource;
  canEdit: boolean;
  canRemove: boolean;
}

export interface ProjectMemberInvite {
  email: string;
  role: ProjectMemberRole;
}

export interface UserLookupResult {
  id: string;
  email: string | null;
  displayName: string | null;
}
