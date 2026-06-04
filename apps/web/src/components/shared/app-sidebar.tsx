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
  Settings,
  Home,
  BarChart3,
  GitCompare,
  LayoutDashboard,
  LineChart,
  FileText,
} from "lucide-react";
import { FRONTEND_ROUTES } from "@/lib/constants/frontend-routes";
import { useCurrentProject } from '@/domain/projects/hooks/project-provider';
import { Skeleton } from '../ui/skeleton';
import { AppLogoMark } from "@/components/shared/app-logo-mark";


const getProjectItems = (projectId: string) => [
  {
    title: "Overview",
    url: FRONTEND_ROUTES.PROJECT_PAGES.OVERVIEW(projectId),
    icon: LayoutDashboard,
  },
  {
    title: "Experiments",
    url: FRONTEND_ROUTES.PROJECT_PAGES.EXPERIMENTS(projectId),
    icon: FlaskConical,
  },
  {
    title: "Metrics",
    url: FRONTEND_ROUTES.PROJECT_PAGES.METRICS(projectId),
    icon: LineChart,
  },
  {
    title: "Reports",
    url: FRONTEND_ROUTES.PROJECT_PAGES.REPORTS(projectId),
    icon: FileText,
  },
  {
    title: "Hypotheses",
    url: FRONTEND_ROUTES.PROJECT_PAGES.HYPOTHESES(projectId),
    icon: Lightbulb,
  },
  {
    title: "Kanban",
    url: FRONTEND_ROUTES.PROJECT_PAGES.KANBAN(projectId),
    icon: KanbanSquare,
  },
  {
    title: "Scalars",
    url: FRONTEND_ROUTES.PROJECT_PAGES.SCALARS(projectId),
    icon: BarChart3,
  },
  {
    title: "Compare",
    url: FRONTEND_ROUTES.PROJECT_PAGES.COMPARE(projectId),
    icon: GitCompare,
  },
  {
    title: "DAG View",
    url: FRONTEND_ROUTES.PROJECT_PAGES.DAG(projectId),
    icon: GitBranch,
  },
  {
    title: "Settings",
    url: FRONTEND_ROUTES.PROJECT_PAGES.SETTINGS(projectId),
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
        <div className="flex items-center gap-2 rounded-md px-2 py-1.5">
          <Link
            href={
              project
                ? FRONTEND_ROUTES.PROJECT_PAGES.OVERVIEW(project.id)
                : FRONTEND_ROUTES.PROJECTS
            }
            className="flex min-w-0 flex-1 items-center gap-2 rounded-md px-0 py-0 hover-elevate active-elevate-2 cursor-pointer"
          >
            <AppLogoMark />
            <div className="flex min-w-0 flex-1 flex-col">
              <span className="truncate text-sm font-semibold tracking-tight">
                Experiment Tracker
              </span>
              <span className="truncate text-xs text-muted-foreground">
                {!isLoading ? (project?.name ?? "—") : "Loading..."}
              </span>
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
        {!isLoading && project && (
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
