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
  LayoutDashboard, 
  FolderKanban, 
  FlaskConical, 
  Lightbulb, 
  KanbanSquare,
  GitBranch,
  Beaker,
  Settings,
  ChevronRight
} from "lucide-react";
import { useExperimentStore } from "@/stores/experiment-store";
import type { Project } from "@shared/schema";

const globalItems = [
  {
    title: "Dashboard",
    url: "/",
    icon: LayoutDashboard,
  },
  {
    title: "Projects",
    url: "/projects",
    icon: FolderKanban,
  },
];

const projectItems = [
  {
    title: "Experiments",
    url: "/experiments",
    icon: FlaskConical,
  },
  {
    title: "Hypotheses",
    url: "/hypotheses",
    icon: Lightbulb,
  },
  {
    title: "Kanban",
    url: "/kanban",
    icon: KanbanSquare,
  },
  {
    title: "DAG View",
    url: "/dag",
    icon: GitBranch,
  },
  {
    title: "Settings",
    url: "/settings",
    icon: Settings,
  },
];

export function AppSidebar() {
  const [location] = useLocation();
  const { 
    selectedProjectId, 
    openProjectSelector 
  } = useExperimentStore();

  const { data: projects } = useQuery<Project[]>({
    queryKey: ["/api/projects"],
  });

  const selectedProject = projects?.find((p) => p.id === selectedProjectId);

  const isActive = (url: string) => {
    if (url === "/") return location === "/";
    return location.startsWith(url);
  };

  return (
    <Sidebar>
      <SidebarHeader className="p-4 border-b border-sidebar-border">
        <button
          onClick={openProjectSelector}
          className="w-full text-left"
          data-testid="button-project-selector"
        >
          <div className="flex items-center gap-2 hover-elevate active-elevate-2 rounded-md px-2 py-1.5 cursor-pointer">
            <div className="flex items-center justify-center w-8 h-8 rounded-md bg-primary text-primary-foreground">
              <Beaker className="w-4 h-4" />
            </div>
            <div className="flex flex-col flex-1 min-w-0">
              <span className="font-semibold text-sm tracking-tight truncate">
                {selectedProject ? selectedProject.name : "ResearchTrack"}
              </span>
              <span className="text-xs text-muted-foreground truncate">
                {selectedProject ? "Click to change project" : "Click to select project"}
              </span>
            </div>
            <ChevronRight className="w-4 h-4 text-muted-foreground flex-shrink-0" />
          </div>
        </button>
      </SidebarHeader>
      <SidebarContent>
        <SidebarGroup>
          <SidebarGroupLabel>Navigation</SidebarGroupLabel>
          <SidebarGroupContent>
            <SidebarMenu>
              {globalItems.map((item) => (
                <SidebarMenuItem key={item.title}>
                  <SidebarMenuButton 
                    asChild 
                    isActive={isActive(item.url)}
                    data-testid={`nav-${item.title.toLowerCase()}`}
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

        {selectedProjectId && (
          <SidebarGroup>
            <SidebarGroupLabel>Project Views</SidebarGroupLabel>
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
      </SidebarContent>
      <SidebarFooter className="p-4 border-t border-sidebar-border">
        <div className="text-xs text-muted-foreground">
          Research-native experiment tracking
        </div>
      </SidebarFooter>
    </Sidebar>
  );
}
