import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Trash2, Pencil, Check, X } from "lucide-react";
import type { ScalarSavedView } from "../types";

interface ScalarViewItemProps {
  view: ScalarSavedView;
  isRenaming: boolean;
  renamingValue: string;
  onChangeRenamingValue: (value: string) => void;
  onStartRename: (view: ScalarSavedView) => void;
  onConfirmRename: () => void;
  onCancelRename: () => void;
  onDelete: (viewId: string) => void;
  onRestore: (query: string) => void;
}

export function ScalarViewItem({
  view,
  isRenaming,
  renamingValue,
  onChangeRenamingValue,
  onStartRename,
  onConfirmRename,
  onCancelRename,
  onDelete,
  onRestore,
}: ScalarViewItemProps) {
  return (
    <div
      className="rounded-md border p-2 cursor-pointer hover:bg-muted/30"
      data-testid={`saved-view-${view.id}`}
      onClick={() => {
        if (!isRenaming) {
          onRestore(view.query);
        }
      }}
    >
      <div className="flex items-center gap-2">
        {isRenaming ? (
          <Input
            value={renamingValue}
            onChange={(event) => onChangeRenamingValue(event.target.value)}
            className="h-8 flex-1"
            data-testid={`input-rename-view-${view.id}`}
            onClick={(event) => event.stopPropagation()}
          />
        ) : (
          <span className="text-sm font-medium truncate flex-1" title={view.name}>
            {view.name}
          </span>
        )}
        <div className="flex items-center gap-1 flex-shrink-0 ml-auto">
          {isRenaming ? (
            <>
              <Button
                variant="ghost"
                size="icon"
                className="h-7 w-7"
                onClick={(event) => {
                  event.stopPropagation();
                  onConfirmRename();
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
                  onCancelRename();
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
                onStartRename(view);
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
              onDelete(view.id);
            }}
            data-testid={`button-delete-view-${view.id}`}
          >
            <Trash2 className="w-3.5 h-3.5" />
          </Button>
        </div>
      </div>
    </div>
  );
}
