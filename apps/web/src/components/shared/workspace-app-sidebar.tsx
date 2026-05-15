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
import { BookOpen, FolderKanban, Home, Users } from "lucide-react";
import { FRONTEND_ROUTES } from "@/lib/constants/frontend-routes";
import { cn } from "@/lib/utils";
import { AppLogoMark } from "@/components/shared/app-logo-mark";

export function WorkspaceAppSidebar() {
  const pathname = usePathname();
  const projectsActive = pathname === FRONTEND_ROUTES.PROJECTS;
  const teamsActive =
    pathname === FRONTEND_ROUTES.TEAMS || pathname?.startsWith(`${FRONTEND_ROUTES.TEAMS}/`);
  const docsActive = pathname === FRONTEND_ROUTES.DOCS || pathname?.startsWith(`${FRONTEND_ROUTES.DOCS}/`);

  return (
    <Sidebar>
      <SidebarHeader className="p-4 border-b border-sidebar-border">
        <div className="flex items-center gap-2 rounded-md px-2 py-1.5">
          <Link
            href={FRONTEND_ROUTES.PROJECTS}
            className="flex min-w-0 flex-1 items-center gap-2 rounded-md px-0 py-0 hover-elevate active-elevate-2 cursor-pointer"
          >
            <AppLogoMark />
            <div className="flex min-w-0 flex-1 flex-col">
              <span className="truncate text-sm font-semibold tracking-tight">Experiment Tracker</span>
              <span className="truncate text-xs text-muted-foreground">Workspace</span>
            </div>
          </Link>
          <Link
            href={FRONTEND_ROUTES.PROJECTS}
            className="hover-elevate active-elevate-2 flex h-8 w-8 flex-shrink-0 items-center justify-center rounded-md text-muted-foreground"
            aria-label="All projects"
            title="All projects"
          >
            <Home className="h-4 w-4" />
          </Link>
        </div>
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
              <SidebarMenuItem>
                <SidebarMenuButton asChild isActive={docsActive}>
                  <Link
                    href={FRONTEND_ROUTES.DOCS}
                    data-testid="nav-workspace-docs"
                    className={cn(docsActive && "font-medium")}
                  >
                    <BookOpen className="w-4 h-4" />
                    <span>Documentation</span>
                  </Link>
                </SidebarMenuButton>
              </SidebarMenuItem>
            </SidebarMenu>
          </SidebarGroupContent>
        </SidebarGroup>
      </SidebarContent>
      <SidebarFooter className="p-4 border-t border-sidebar-border">
        <div className="text-xs text-muted-foreground">Projects, teams, and docs</div>
      </SidebarFooter>
    </Sidebar>
  );
}
