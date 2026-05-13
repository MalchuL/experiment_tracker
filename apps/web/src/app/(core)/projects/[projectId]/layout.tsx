"use client";
import { SidebarProvider, SidebarInset } from "@/components/ui/sidebar";
import { AppSidebar } from "@/components/shared/app-sidebar";
import { SidebarTrigger } from "@/components/ui/sidebar";
import { ThemeToggle } from "@/components/shared/theme-toggle";
import { UserMenu } from "@/components/shared/user-menu";
import { WorkspaceDocsNav } from "@/components/shared/workspace-docs-nav";
import { ProjectProvider } from "@/domain/projects/hooks";
import { useParams, usePathname } from "next/navigation";

export default function ProjectLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const sidebarStyle = {
    "--sidebar-width": "16rem",
    "--sidebar-width-icon": "3rem",
  };

  const { projectId } = useParams<{ projectId: string }>();
  // Route-specific shell: DAG and metrics are full-bleed in the inset (no `container` centering or p-6).
  const pathname = usePathname();
  const isDagPage = pathname?.endsWith("/dag");
  const isMetricsPage = pathname?.endsWith("/metrics");
  const isExperimentsPage = pathname?.endsWith("/experiments");
  const isKanbanPage = pathname?.endsWith("/kanban");
  const isScalarsPage = pathname?.endsWith("/scalars");

  const containerClassName = isDagPage
    ? "flex h-full min-h-0 w-full max-w-none flex-col p-0"
    : isMetricsPage || isExperimentsPage || isKanbanPage || isScalarsPage
      ? "flex h-full min-h-0 w-full max-w-none flex-col p-0"
      : "container max-w-screen-2xl mx-auto p-6";

  return (
    <SidebarProvider style={sidebarStyle as React.CSSProperties}>
      <div className="flex h-screen w-full">
        <ProjectProvider projectId={projectId}>
          <AppSidebar />
          <SidebarInset className="flex flex-col flex-1 overflow-hidden">
            <header className="flex items-center justify-between gap-2 h-14 px-4 border-b bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60 sticky top-0 z-50">
              <div className="flex min-w-0 flex-1 items-center gap-3">
                <SidebarTrigger data-testid="button-sidebar-toggle" />
                <WorkspaceDocsNav className="hidden sm:flex" />
              </div>
              <div className="flex items-center gap-2">
                <ThemeToggle />
                <UserMenu />
              </div>
            </header>
            <main className="min-h-0 flex-1 overflow-auto">
              <div className={containerClassName}>{children}</div>
            </main>
          </SidebarInset>
        </ProjectProvider>
      </div>
    </SidebarProvider >
  );
}
