import { Switch, Route } from "wouter";
import { queryClient } from "./lib/queryClient";
import { QueryClientProvider } from "@tanstack/react-query";
import { Toaster } from "@/components/ui/toaster";
import { TooltipProvider } from "@/components/ui/tooltip";
import { ThemeProvider } from "@/lib/theme-provider";
import { ThemeToggle } from "@/components/theme-toggle";
import { 
  SidebarProvider, 
  SidebarTrigger,
  SidebarInset 
} from "@/components/ui/sidebar";
import { AppSidebar } from "@/components/app-sidebar";
import { ProjectSelector } from "@/components/project-selector";

import Dashboard from "@/pages/dashboard";
import Projects from "@/pages/projects";
import ProjectDetail from "@/pages/project-detail";
import Experiments from "@/pages/experiments";
import ExperimentDetail from "@/pages/experiment-detail";
import Hypotheses from "@/pages/hypotheses";
import HypothesisDetail from "@/pages/hypothesis-detail";
import Kanban from "@/pages/kanban";
import DAGView from "@/pages/dag-view";
import ProjectSettings from "@/pages/project-settings";
import NotFound from "@/pages/not-found";

function Router() {
  return (
    <Switch>
      <Route path="/" component={Dashboard} />
      <Route path="/projects" component={Projects} />
      <Route path="/projects/:id" component={ProjectDetail} />
      <Route path="/experiments" component={Experiments} />
      <Route path="/experiments/:id" component={ExperimentDetail} />
      <Route path="/hypotheses" component={Hypotheses} />
      <Route path="/hypotheses/:id" component={HypothesisDetail} />
      <Route path="/kanban" component={Kanban} />
      <Route path="/dag" component={DAGView} />
      <Route path="/settings" component={ProjectSettings} />
      <Route component={NotFound} />
    </Switch>
  );
}

function App() {
  const sidebarStyle = {
    "--sidebar-width": "16rem",
    "--sidebar-width-icon": "3rem",
  };

  return (
    <QueryClientProvider client={queryClient}>
      <ThemeProvider defaultTheme="system" storageKey="researchtrack-theme">
        <TooltipProvider>
          <SidebarProvider style={sidebarStyle as React.CSSProperties}>
            <div className="flex h-screen w-full">
              <AppSidebar />
              <SidebarInset className="flex flex-col flex-1 overflow-hidden">
                <header className="flex items-center justify-between gap-2 h-14 px-4 border-b bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60 sticky top-0 z-50">
                  <SidebarTrigger data-testid="button-sidebar-toggle" />
                  <ThemeToggle />
                </header>
                <main className="flex-1 overflow-auto">
                  <div className="container max-w-screen-2xl mx-auto p-6">
                    <Router />
                  </div>
                </main>
              </SidebarInset>
            </div>
          </SidebarProvider>
          <ProjectSelector />
          <Toaster />
        </TooltipProvider>
      </ThemeProvider>
    </QueryClientProvider>
  );
}

export default App;
