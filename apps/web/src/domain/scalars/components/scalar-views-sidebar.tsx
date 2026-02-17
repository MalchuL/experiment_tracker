import { useMemo, useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Separator } from "@/components/ui/separator";
import { RightSidebarShell } from "@/components/shared/right-sidebar-shell";
import { Save, Trash2, Pencil, Check, X } from "lucide-react";
import { useScalarViews } from "../hooks";
import type { ScalarSavedView } from "../types";

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
                <div
                  key={view.id}
                  className="rounded-md border p-2 space-y-2 cursor-pointer hover:bg-muted/30"
                  data-testid={`saved-view-${view.id}`}
                  onClick={() => {
                    if (renamingId !== view.id) {
                      onRestoreView(view.query);
                    }
                  }}
                >
                  <div className="flex items-center gap-2">
                    {renamingId === view.id ? (
                      <Input
                        value={renamingValue}
                        onChange={(event) => setRenamingValue(event.target.value)}
                        className="h-8"
                        data-testid={`input-rename-view-${view.id}`}
                        onClick={(event) => event.stopPropagation()}
                      />
                    ) : (
                      <span className="text-sm font-medium truncate flex-1" title={view.name}>
                        {view.name}
                      </span>
                    )}
                  </div>

                  <div className="flex items-center gap-1">
                    {renamingId === view.id ? (
                      <>
                        <Button
                          variant="ghost"
                          size="icon"
                          className="h-7 w-7"
                          onClick={(event) => {
                            event.stopPropagation();
                            commitRename();
                          }}
                          data-testid={`button-confirm-rename-view-${view.id}`}
                        >
                          <Check className="w-3.5 h-3.5" />
                        </Button>
                        <Button
                          variant="ghost"
                          size="icon"
                          className="h-7 w-7"
                          onClick={(event) => {
                            event.stopPropagation();
                            setRenamingId(null);
                            setRenamingValue("");
                          }}
                          data-testid={`button-cancel-rename-view-${view.id}`}
                        >
                          <X className="w-3.5 h-3.5" />
                        </Button>
                      </>
                    ) : (
                      <Button
                        variant="ghost"
                        size="icon"
                        className="h-7 w-7"
                        onClick={(event) => {
                          event.stopPropagation();
                          startRename(view);
                        }}
                        data-testid={`button-rename-view-${view.id}`}
                      >
                        <Pencil className="w-3.5 h-3.5" />
                      </Button>
                    )}

                    <Button
                      variant="ghost"
                      size="icon"
                      className="h-7 w-7"
                      onClick={(event) => {
                        event.stopPropagation();
                        deleteView(view.id);
                      }}
                      data-testid={`button-delete-view-${view.id}`}
                    >
                      <Trash2 className="w-3.5 h-3.5" />
                    </Button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </ScrollArea>
      </div>
    </RightSidebarShell>
  );
}
