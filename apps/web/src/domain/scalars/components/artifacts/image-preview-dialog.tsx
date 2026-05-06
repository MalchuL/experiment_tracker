"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";

type InterpolationMode = "auto" | "pixelated" | "crisp-edges";

interface ImagePreviewDialogProps {
  imagePreview: { src: string; title: string } | null;
  onOpenChange: (open: boolean) => void;
}

const INTERPOLATION_OPTIONS: Array<{ value: InterpolationMode; label: string }> = [
  { value: "auto", label: "Smooth" },
  { value: "pixelated", label: "Pixel" },
  { value: "crisp-edges", label: "Sharp" },
];

export function ImagePreviewDialog({
  imagePreview,
  onOpenChange,
}: ImagePreviewDialogProps) {
  const [interpolationMode, setInterpolationMode] = useState<InterpolationMode>("auto");

  return (
    <Dialog open={!!imagePreview} onOpenChange={onOpenChange}>
      <DialogContent className="flex h-[84vh] w-[96vw] max-w-[96vw] flex-col overflow-hidden p-3">
        <DialogHeader>
          <DialogTitle className="flex items-center justify-between gap-4 pr-8">
            <span className="min-w-0 truncate">{imagePreview?.title ?? "Image preview"}</span>
            <div className="flex shrink-0 items-center gap-1">
              {INTERPOLATION_OPTIONS.map((option) => (
                <Button
                  key={option.value}
                  type="button"
                  variant={interpolationMode === option.value ? "default" : "outline"}
                  size="sm"
                  className="h-7 px-2 text-xs"
                  onClick={() => setInterpolationMode(option.value)}
                >
                  {option.label}
                </Button>
              ))}
            </div>
          </DialogTitle>
        </DialogHeader>
        <div className="flex min-h-0 flex-1 items-center justify-center overflow-hidden rounded-md bg-muted/20">
          {imagePreview ? (
            <img
              src={imagePreview.src}
              alt={imagePreview.title}
              className="h-full w-full object-contain"
              style={{ imageRendering: interpolationMode }}
            />
          ) : null}
        </div>
      </DialogContent>
    </Dialog>
  );
}
