"use client";
import { SidebarProvider, SidebarInset } from "@/components/ui/sidebar";
import { AppSidebar } from "@/components/shared/app-sidebar";
import { SidebarTrigger } from "@/components/ui/sidebar";
import { ThemeToggle } from "@/components/shared/theme-toggle";
import { UserMenu } from "@/components/shared/user-menu";
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
  // Dirty hack to get the container class name for the DAG page
  const pathname = usePathname();
  const isDagPage = pathname?.endsWith("/dag");
  const containerClassName = isDagPage
    ? "w-full max-w-none p-0 h-full flex flex-col"
    : "container max-w-screen-2xl mx-auto p-6";

  return (
    <SidebarProvider style={sidebarStyle as React.CSSProperties}>
      <div className="flex h-screen w-full">
        <ProjectProvider projectId={projectId}>
          <AppSidebar />
          <SidebarInset className="flex flex-col flex-1 overflow-hidden">
            <header className="flex items-center justify-between gap-2 h-14 px-4 border-b bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60 sticky top-0 z-50">
              <SidebarTrigger data-testid="button-sidebar-toggle" />
              <div className="flex items-center gap-2">
                <ThemeToggle />
                <UserMenu />
              </div>
            </header>
            <main className="flex-1 overflow-auto">
              <div className={containerClassName}>{children}</div>
            </main>
          </SidebarInset>
        </ProjectProvider>
      </div>
    </SidebarProvider >
  );
}
