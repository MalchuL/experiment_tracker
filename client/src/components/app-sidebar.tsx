import { Link, useLocation } from "wouter";
import { useQuery } from "@tanstack/react-query";
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
import type { Project } from "@shared/schema";

function getProjectIdFromPath(path: string): string | null {
  const match = path.match(/^\/projects\/([^/]+)/);
  return match ? match[1] : null;
}

const getProjectItems = (projectId: string) => [
  {
    title: "Overview",
    url: `/projects/${projectId}`,
    icon: LayoutDashboard,
  },
  {
    title: "Experiments",
    url: `/projects/${projectId}/experiments`,
    icon: FlaskConical,
  },
  {
    title: "Hypotheses",
    url: `/projects/${projectId}/hypotheses`,
    icon: Lightbulb,
  },
  {
    title: "Kanban",
    url: `/projects/${projectId}/kanban`,
    icon: KanbanSquare,
  },
  {
    title: "Scalars",
    url: `/projects/${projectId}/scalars`,
    icon: BarChart3,
  },
  {
    title: "DAG View",
    url: `/projects/${projectId}/dag`,
    icon: GitBranch,
  },
  {
    title: "Settings",
    url: `/projects/${projectId}/settings`,
    icon: Settings,
  },
];

export function AppSidebar() {
  const [location] = useLocation();
  
  const projectIdFromUrl = getProjectIdFromPath(location);

  const { data: projects } = useQuery<Project[]>({
    queryKey: ["/api/projects"],
  });

  const selectedProject = projectIdFromUrl 
    ? projects?.find((p) => p.id === projectIdFromUrl)
    : null;

  const isActive = (url: string) => {
    return location === url;
  };

  const projectItems = projectIdFromUrl ? getProjectItems(projectIdFromUrl) : [];

  return (
    <Sidebar>
      <SidebarHeader className="p-4 border-b border-sidebar-border">
        <Link href="/">
          <div className="flex items-center gap-2 hover-elevate active-elevate-2 rounded-md px-2 py-1.5 cursor-pointer">
            <div className="flex items-center justify-center w-8 h-8 rounded-md bg-primary text-primary-foreground">
              <Beaker className="w-4 h-4" />
            </div>
            <div className="flex flex-col flex-1 min-w-0">
              <span className="font-semibold text-sm tracking-tight truncate">
                ResearchTrack
              </span>
              <span className="text-xs text-muted-foreground truncate">
                {selectedProject ? selectedProject.name : "All Projects"}
              </span>
            </div>
            <Home className="w-4 h-4 text-muted-foreground flex-shrink-0" />
          </div>
        </Link>
      </SidebarHeader>
      <SidebarContent>
        {projectIdFromUrl && selectedProject && (
          <SidebarGroup>
            <SidebarGroupLabel>{selectedProject.name}</SidebarGroupLabel>
            <SidebarGroupContent>
              <SidebarMenu>
                {projectItems.map((item) => (
                  <SidebarMenuItem key={item.title}>
                    <SidebarMenuButton 
                      asChild 
                      isActive={isActive(item.url)}
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

        {!projectIdFromUrl && (
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
