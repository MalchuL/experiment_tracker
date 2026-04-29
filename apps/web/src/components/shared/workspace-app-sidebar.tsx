"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  Sidebar,
  SidebarContent,
  SidebarFooter,
  SidebarGroup,
  SidebarGroupContent,
  SidebarGroupLabel,
  SidebarHeader,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
} from "@/components/ui/sidebar";
import { Beaker, FolderKanban, Home, Users } from "lucide-react";
import { FRONTEND_ROUTES } from "@/lib/constants/frontend-routes";
import { cn } from "@/lib/utils";

export function WorkspaceAppSidebar() {
  const pathname = usePathname();
  const projectsActive = pathname === FRONTEND_ROUTES.PROJECTS;
  const teamsActive =
    pathname === FRONTEND_ROUTES.TEAMS || pathname?.startsWith(`${FRONTEND_ROUTES.TEAMS}/`);

  return (
    <Sidebar>
      <SidebarHeader className="p-4 border-b border-sidebar-border">
        <Link href={FRONTEND_ROUTES.PROJECTS}>
          <div className="flex items-center gap-2 hover-elevate active-elevate-2 rounded-md px-2 py-1.5 cursor-pointer">
            <div className="flex items-center justify-center w-8 h-8 rounded-md bg-primary text-primary-foreground">
              <Beaker className="w-4 h-4" />
            </div>
            <div className="flex flex-col flex-1 min-w-0">
              <span className="font-semibold text-sm tracking-tight truncate">ResearchTrack</span>
              <span className="text-xs text-muted-foreground truncate">Workspace</span>
            </div>
            <Home className="w-4 h-4 text-muted-foreground flex-shrink-0" />
          </div>
        </Link>
      </SidebarHeader>
      <SidebarContent>
        <SidebarGroup>
          <SidebarGroupLabel>Navigate</SidebarGroupLabel>
          <SidebarGroupContent>
            <SidebarMenu>
              <SidebarMenuItem>
                <SidebarMenuButton asChild isActive={projectsActive}>
                  <Link
                    href={FRONTEND_ROUTES.PROJECTS}
                    data-testid="nav-workspace-projects"
                    className={cn(projectsActive && "font-medium")}
                  >
                    <FolderKanban className="w-4 h-4" />
                    <span>Projects</span>
                  </Link>
                </SidebarMenuButton>
              </SidebarMenuItem>
              <SidebarMenuItem>
                <SidebarMenuButton asChild isActive={teamsActive}>
                  <Link
                    href={FRONTEND_ROUTES.TEAMS}
                    data-testid="nav-workspace-teams"
                    className={cn(teamsActive && "font-medium")}
                  >
                    <Users className="w-4 h-4" />
                    <span>Teams</span>
                  </Link>
                </SidebarMenuButton>
              </SidebarMenuItem>
            </SidebarMenu>
          </SidebarGroupContent>
        </SidebarGroup>
      </SidebarContent>
      <SidebarFooter className="p-4 border-t border-sidebar-border">
        <div className="text-xs text-muted-foreground">Projects and teams</div>
      </SidebarFooter>
    </Sidebar>
  );
}
