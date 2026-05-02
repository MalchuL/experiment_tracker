"use client";

import { useMemo, useState } from "react";
import { Save } from "lucide-react";
import { Button } from "@/components/ui/button";
import { ScrollArea } from "@/components/ui/scroll-area";
import { useScalarViews } from "@/domain/scalars/hooks";
import type { ScalarSavedView } from "@/domain/scalars/types";
import { ScalarViewItem } from "@/domain/scalars/components/scalar-view-item";

interface ScalarSavedViewsSectionProps {
  projectId?: string;
  currentQuery: string;
  onRestoreView: (query: string) => void;
}

export function ScalarSavedViewsSection({
  projectId,
  currentQuery,
  onRestoreView,
}: ScalarSavedViewsSectionProps) {
  const { views, hydrated, saveCurrentView, renameView, deleteView } = useScalarViews(projectId);
  const [renamingId, setRenamingId] = useState<string | null>(null);
  const [renamingValue, setRenamingValue] = useState("");
  const list = useMemo(() => views, [views]);

  const startRename = (view: ScalarSavedView) => {
    setRenamingId(view.id);
    setRenamingValue(view.name);
  };

  const commitRename = () => {
    if (!renamingId) return;
    renameView(renamingId, renamingValue);
    setRenamingId(null);
    setRenamingValue("");
  };

  return (
    <div className="space-y-3">
      <Button
        onClick={() => saveCurrentView(currentQuery)}
        disabled={!projectId}
        className="h-8 w-full text-xs"
        data-testid="button-save-current-view"
      >
        <Save className="mr-2 h-3.5 w-3.5" />
        Save current view
      </Button>
      <ScrollArea className="h-40">
        {!hydrated ? (
          <p className="text-xs text-muted-foreground">Loading saved views...</p>
        ) : list.length === 0 ? (
          <p className="text-xs text-muted-foreground">No saved views yet.</p>
        ) : (
          <div className="space-y-2 pr-2">
            {list.map((view) => (
              <ScalarViewItem
                key={view.id}
                view={view}
                isRenaming={renamingId === view.id}
                renamingValue={renamingValue}
                onChangeRenamingValue={setRenamingValue}
                onStartRename={startRename}
                onConfirmRename={commitRename}
                onCancelRename={() => {
                  setRenamingId(null);
                  setRenamingValue("");
                }}
                onDelete={deleteView}
                onRestore={onRestoreView}
              />
            ))}
          </div>
        )}
      </ScrollArea>
    </div>
  );
}
