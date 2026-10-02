"use client";

import { RotateCcw } from "lucide-react";
import { Button } from "@/components/ui/button";
import { LiveRefreshIndicator } from "./live-refresh-indicator";

export interface ScalarsPageActionsProps {
  refresh: {
    isFetching: boolean;
    onRefresh: () => Promise<void>;
    autoRefreshEnabled: boolean;
    cycleStartMs: number;
    onToggleAutoRefresh: () => void;
  };
  sidebars: {
    experiments: { open: boolean; toggle: () => void };
    settings: { open: boolean; toggle: () => void };
  };
}

export function ScalarsPageActions({
  refresh,
  sidebars,
}: ScalarsPageActionsProps) {
  return (
    <div className="flex items-center gap-2">
      <LiveRefreshIndicator
        enabled={refresh.autoRefreshEnabled}
        cycleStartMs={refresh.cycleStartMs}
        onToggle={refresh.onToggleAutoRefresh}
      />
      <Button
        variant="outline"
        size="sm"
        onClick={() => void refresh.onRefresh()}
        disabled={refresh.isFetching}
        data-testid="button-refresh-scalars"
      >
        <RotateCcw
          className={`mr-2 h-4 w-4 ${refresh.isFetching ? "animate-spin" : ""}`}
        />
        {refresh.isFetching ? "Refreshing..." : "Refresh"}
      </Button>
      <Button
        variant="outline"
        size="sm"
        onClick={sidebars.experiments.toggle}
        data-testid="button-toggle-experiments-sidebar"
      >
        {sidebars.experiments.open ? "Hide Experiments" : "Show Experiments"}
      </Button>
      <Button
        variant="outline"
        size="sm"
        onClick={sidebars.settings.toggle}
        data-testid="button-toggle-views-sidebar"
      >
        {sidebars.settings.open ? "Hide Settings" : "Show Settings"}
      </Button>
    </div>
  );
}
