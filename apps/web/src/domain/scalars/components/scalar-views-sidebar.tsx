import { useMemo, useState } from "react";
import { Button } from "@/components/ui/button";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Separator } from "@/components/ui/separator";
import { RightSidebarShell } from "@/components/shared/right-sidebar-shell";
import { Save } from "lucide-react";
import { useScalarViews } from "../hooks";
import type { ScalarSavedView } from "../types";
import { ScalarViewItem } from "./scalar-view-item";

interface ScalarViewsSidebarProps {
  projectId?: string;
  currentQuery: string;
  onRestoreView: (query: string) => void;
  onClose?: () => void;
}

export function ScalarViewsSidebar({
  projectId,
  currentQuery,
  onRestoreView,
  onClose,
}: ScalarViewsSidebarProps) {
  const { views, hydrated, saveCurrentView, renameView, deleteView } =
    useScalarViews(projectId);
  const [renamingId, setRenamingId] = useState<string | null>(null);
  const [renamingValue, setRenamingValue] = useState("");

  const canSave = !!projectId;
  const hasViews = views.length > 0;
  const list = useMemo(() => views, [views]);

  const handleSave = () => {
    saveCurrentView(currentQuery);
  };

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
    <RightSidebarShell title="Saved Views" onClose={onClose} widthClassName="w-80" testId="scalars-views-sidebar">
      <div className="flex-1 overflow-hidden flex flex-col gap-3 p-4">
        <Button
          onClick={handleSave}
          disabled={!canSave}
          className="w-full"
          data-testid="button-save-current-view"
        >
          <Save className="w-4 h-4 mr-2" />
          Save Current View
        </Button>

        <Separator />

        <ScrollArea className="flex-1">
          {!hydrated ? (
            <p className="text-sm text-muted-foreground">Loading saved views...</p>
          ) : !hasViews ? (
            <p className="text-sm text-muted-foreground">
              No saved views yet for this project.
            </p>
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
    </RightSidebarShell>
  );
}
