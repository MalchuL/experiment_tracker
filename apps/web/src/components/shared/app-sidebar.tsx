"use client";
import Link from 'next/link'
import {
  Sidebar,
  SidebarContent,
  SidebarGroup,
  SidebarGroupContent,
  SidebarGroupLabel,
  SidebarHeader,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
  SidebarFooter,
} from "@/components/ui/sidebar";
import { 
  FlaskConical, 
  Lightbulb, 
  KanbanSquare,
  GitBranch,
  Beaker,
  Settings,
  Home,
  BarChart3,
  LayoutDashboard
} from "lucide-react";
import { FRONTEND_ROUTES } from "@/lib/constants/frontend-routes";
import { useParams } from "next/navigation";
import { useProject } from "@/domain/projects/hooks/project-hook";
import { useCurrentProject } from '@/domain/projects/hooks/project-provider';
import { Skeleton } from '../ui/skeleton';


const getProjectItems = (projectId: string) => [
  {
    title: "Overview",
    url: FRONTEND_ROUTES.BY_ID.PROJECT(projectId),
    icon: LayoutDashboard,
  },
  {
    title: "Experiments",
    url: FRONTEND_ROUTES.BY_ID.EXPERIMENT(projectId),
    icon: FlaskConical,
  },
  {
    title: "Hypotheses",
    url: FRONTEND_ROUTES.BY_ID.HYPOTHESIS(projectId),
    icon: Lightbulb,
  },
  {
    title: "Kanban",
    url: FRONTEND_ROUTES.BY_ID.KANBAN(projectId),
    icon: KanbanSquare,
  },
  {
    title: "Scalars",
    url: FRONTEND_ROUTES.BY_ID.SCALARS(projectId),
    icon: BarChart3,
  },
  {
    title: "DAG View",
    url: FRONTEND_ROUTES.BY_ID.DAG(projectId),
    icon: GitBranch,
  },
  {
    title: "Settings",
    url: FRONTEND_ROUTES.BY_ID.SETTINGS(projectId),
    icon: Settings,
  },
];

export function SidebarSkeleton() {
  return (
    <Sidebar>
      <SidebarHeader className="p-4 border-b border-sidebar-border">
        <Skeleton className="w-full h-8" />
      </SidebarHeader>
    </Sidebar>
  );
}

export function AppSidebar() {
  const { project, isLoading } = useCurrentProject();

  const projectItems = project ? getProjectItems(project.id) : [];
  if (isLoading) {
    return <SidebarSkeleton />;
  }
  return (
    <Sidebar>
      <SidebarHeader className="p-4 border-b border-sidebar-border">
        <Link href={FRONTEND_ROUTES.ROOT}>
          <div className="flex items-center gap-2 hover-elevate active-elevate-2 rounded-md px-2 py-1.5 cursor-pointer">
            <div className="flex items-center justify-center w-8 h-8 rounded-md bg-primary text-primary-foreground">
              <Beaker className="w-4 h-4" />
            </div>
            <div className="flex flex-col flex-1 min-w-0">
              <span className="font-semibold text-sm tracking-tight truncate">
                ResearchTrack
              </span>
              <span className="text-xs text-muted-foreground truncate">
                {!isLoading ? project.name : "Loading..."}
              </span>
            </div>
            <Home className="w-4 h-4 text-muted-foreground flex-shrink-0" />
          </div>
        </Link>
      </SidebarHeader>
      <SidebarContent>
        {!isLoading && (
          <SidebarGroup>
            <SidebarGroupLabel>{project.name}</SidebarGroupLabel>
            <SidebarGroupContent>
              <SidebarMenu>
                {projectItems.map((item) => (
                  <SidebarMenuItem key={item.title}>
                    <SidebarMenuButton 
                      asChild 
                      data-testid={`nav-${item.title.toLowerCase().replace(" ", "-")}`}
                    >
                      <Link href={item.url}>
                        <item.icon className="w-4 h-4" />
                        <span>{item.title}</span>
                      </Link>
                    </SidebarMenuButton>
                  </SidebarMenuItem>
                ))}
              </SidebarMenu>
            </SidebarGroupContent>
          </SidebarGroup>
        )}

        {!project && (
          <SidebarGroup>
            <SidebarGroupContent>
              <div className="px-3 py-8 text-center text-sm text-muted-foreground">
                Select a project to see navigation options
              </div>
            </SidebarGroupContent>
          </SidebarGroup>
        )}
      </SidebarContent>
      <SidebarFooter className="p-4 border-t border-sidebar-border">
        <div className="text-xs text-muted-foreground">
          Research-native experiment tracking
        </div>
      </SidebarFooter>
    </Sidebar>
  );
}
