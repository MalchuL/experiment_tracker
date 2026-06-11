import { Loader2, Upload } from "lucide-react";
import type { RefObject } from "react";
import { cn } from "@/lib/utils";

export interface FileDropzoneProps {
  fileInputRef: RefObject<HTMLInputElement | null>;
  handleBoxClick: () => void;
  handleDragOver: (e: React.DragEvent) => void;
  handleDrop: (e: React.DragEvent) => void;
  handleFileSelect: (files: FileList | null) => void;
  inputId?: string;
  title?: string;
  description?: string;
  browseLabel?: string;
  hint?: string;
  accept?: string;
  multiple?: boolean;
  disabled?: boolean;
  isUploading?: boolean;
  compact?: boolean;
  className?: string;
  inputTestId?: string;
}

export function FileDropzone({
  fileInputRef,
  handleBoxClick,
  handleDragOver,
  handleDrop,
  handleFileSelect,
  inputId = "fileUpload",
  title = "Upload a file",
  description = "Drag and drop a file here",
  browseLabel = "click to browse",
  hint,
  accept,
  multiple = false,
  disabled = false,
  isUploading = false,
  compact = false,
  className,
  inputTestId,
}: FileDropzoneProps) {
  const inactive = disabled || isUploading;

  return (
    <div className={cn(compact ? "" : "px-6", className)}>
      <div
        className={cn(
          "flex flex-col items-center justify-center rounded-md border-2 border-dashed text-center transition-colors",
          "border-border/80 bg-muted dark:bg-accent",
          compact ? "p-4" : "p-8",
          inactive
            ? "cursor-not-allowed opacity-60"
            : "cursor-pointer hover:border-primary/45 hover:bg-muted/90 dark:hover:bg-accent/90"
        )}
        onClick={inactive ? undefined : handleBoxClick}
        onDragOver={inactive ? undefined : handleDragOver}
        onDrop={inactive ? undefined : handleDrop}
        data-testid="file-dropzone"
      >
        <div
          className={cn(
            "mb-2 rounded-full ring-1 ring-border/50",
            "bg-background/80 dark:bg-card/90",
            compact ? "p-2" : "p-3"
          )}
        >
          {isUploading ? (
            <Loader2 className={cn("animate-spin text-muted-foreground", compact ? "h-4 w-4" : "h-5 w-5")} />
          ) : (
            <Upload className={cn("text-muted-foreground", compact ? "h-4 w-4" : "h-5 w-5")} />
          )}
        </div>
        <p className={cn("font-medium text-foreground", compact ? "text-xs" : "text-sm")}>
          {isUploading ? "Uploading…" : title}
        </p>
        {!isUploading ? (
          <p className={cn("mt-1 text-muted-foreground", compact ? "text-xs" : "text-sm")}>
            {description ? (
              <>
                {description}
                , or{" "}
              </>
            ) : null}
            <label
              htmlFor={inputId}
              className="font-medium text-primary hover:text-primary/90 cursor-pointer"
              onClick={(event) => event.stopPropagation()}
            >
              {browseLabel}
            </label>
            {hint ? ` (${hint})` : null}
          </p>
        ) : null}
        <input
          type="file"
          id={inputId}
          ref={fileInputRef}
          className="hidden"
          accept={accept}
          multiple={multiple}
          disabled={inactive}
          data-testid={inputTestId}
          onChange={(event) => handleFileSelect(event.target.files)}
        />
      </div>
    </div>
  );
}
