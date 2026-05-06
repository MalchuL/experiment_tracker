"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { FolderKanban, Users } from "lucide-react";
import { SidebarInset, SidebarProvider, SidebarTrigger } from "@/components/ui/sidebar";
import { ThemeToggle } from "@/components/shared/theme-toggle";
import { UserMenu } from "@/components/shared/user-menu";
import { WorkspaceAppSidebar } from "@/components/shared/workspace-app-sidebar";
import { Button } from "@/components/ui/button";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { FRONTEND_ROUTES } from "@/lib/constants/frontend-routes";
import { WorkspaceDocsNav } from "@/components/shared/workspace-docs-nav";
import { cn } from "@/lib/utils";

type WorkspaceHeaderContextValue = {
  setHeaderActions: (node: ReactNode | null) => void;
};

const WorkspaceHeaderContext = createContext<WorkspaceHeaderContextValue | null>(null);

export function useWorkspaceHeaderActions(node: ReactNode | null) {
  const ctx = useContext(WorkspaceHeaderContext);
  useEffect(() => {
    if (!ctx) return;
    ctx.setHeaderActions(node);
    return () => ctx.setHeaderActions(null);
  }, [ctx, node]);
}

function WorkspaceScopeCircles() {
  const pathname = usePathname();
  const projectsActive = pathname === FRONTEND_ROUTES.PROJECTS;
  const teamsActive =
    pathname === FRONTEND_ROUTES.TEAMS || pathname?.startsWith(`${FRONTEND_ROUTES.TEAMS}/`);

  const itemClass = (active: boolean) =>
    cn(
      "h-10 w-10 rounded-full border bg-background shadow-sm flex items-center justify-center transition-colors",
      active
        ? "border-primary text-primary ring-2 ring-primary/25"
        : "border-border text-muted-foreground hover:bg-muted/60 hover:text-foreground",
    );

  return (
    <TooltipProvider delayDuration={300}>
      <div className="flex items-center gap-2">
        <Tooltip>
          <TooltipTrigger asChild>
            <Button variant="ghost" size="icon" className="rounded-full h-10 w-10 p-0" asChild>
              <Link
                href={FRONTEND_ROUTES.PROJECTS}
                aria-label="Projects"
                aria-current={projectsActive ? "page" : undefined}
                data-testid="workspace-scope-projects"
              >
                <span className={itemClass(projectsActive)}>
                  <FolderKanban className="h-4 w-4" />
                </span>
              </Link>
            </Button>
          </TooltipTrigger>
          <TooltipContent side="bottom">Projects</TooltipContent>
        </Tooltip>
        <Tooltip>
          <TooltipTrigger asChild>
            <Button variant="ghost" size="icon" className="rounded-full h-10 w-10 p-0" asChild>
              <Link
                href={FRONTEND_ROUTES.TEAMS}
                aria-label="Teams"
                aria-current={teamsActive ? "page" : undefined}
                data-testid="workspace-scope-teams"
              >
                <span className={itemClass(teamsActive)}>
                  <Users className="h-4 w-4" />
                </span>
              </Link>
            </Button>
          </TooltipTrigger>
          <TooltipContent side="bottom">Teams</TooltipContent>
        </Tooltip>
      </div>
    </TooltipProvider>
  );
}

export function WorkspaceShell({ children }: { children: ReactNode }) {
  const [headerActions, setHeaderActionsState] = useState<ReactNode | null>(null);
  const setHeaderActions = useCallback((node: ReactNode | null) => {
    setHeaderActionsState(node);
  }, []);

  const headerCtx = useMemo(() => ({ setHeaderActions }), [setHeaderActions]);

  const sidebarStyle = {
    "--sidebar-width": "16rem",
    "--sidebar-width-icon": "3rem",
  } as React.CSSProperties;

  return (
    <WorkspaceHeaderContext.Provider value={headerCtx}>
      <SidebarProvider style={sidebarStyle}>
        <div className="flex h-screen w-full">
          <WorkspaceAppSidebar />
          <SidebarInset className="flex flex-col flex-1 overflow-hidden">
            <header className="flex h-14 min-h-14 items-center justify-between gap-2 border-b bg-background/95 px-4 backdrop-blur supports-[backdrop-filter]:bg-background/60 sticky top-0 z-50">
              <div className="flex min-w-0 flex-1 items-center gap-3">
                <SidebarTrigger data-testid="button-workspace-sidebar-toggle" />
                <WorkspaceDocsNav className="hidden sm:flex" />
                <WorkspaceScopeCircles />
              </div>
              <div className="flex flex-shrink-0 flex-wrap items-center justify-end gap-2">
                {headerActions}
                <ThemeToggle />
                <UserMenu />
              </div>
            </header>
            <main className="flex-1 overflow-auto">{children}</main>
          </SidebarInset>
        </div>
      </SidebarProvider>
    </WorkspaceHeaderContext.Provider>
  );
}
