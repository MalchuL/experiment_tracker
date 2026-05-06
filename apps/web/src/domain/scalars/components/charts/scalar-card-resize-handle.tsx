"use client";

import { useCallback } from "react";

interface ScalarCardResizeHandleProps {
  width: number;
  height: number;
  onResize: (size: { width: number; height: number }) => void;
}

export function ScalarCardResizeHandle({
  width,
  height,
  onResize,
}: ScalarCardResizeHandleProps) {
  const handlePointerDown = useCallback(
    (event: React.PointerEvent<HTMLButtonElement>) => {
      event.preventDefault();
      const startX = event.clientX;
      const startY = event.clientY;
      const startWidth = width;
      const startHeight = height;

      const handlePointerMove = (moveEvent: PointerEvent) => {
        onResize({
          width: clamp(startWidth + moveEvent.clientX - startX, 480, 1520),
          height: clamp(startHeight + moveEvent.clientY - startY, 320, 1120),
        });
      };

      const handlePointerUp = () => {
        window.removeEventListener("pointermove", handlePointerMove);
        window.removeEventListener("pointerup", handlePointerUp);
      };

      window.addEventListener("pointermove", handlePointerMove);
      window.addEventListener("pointerup", handlePointerUp);
    },
    [height, onResize, width]
  );

  return (
    <button
      type="button"
      aria-label="Resize scalar cards"
      className="absolute bottom-1 right-1 h-4 w-4 cursor-nwse-resize rounded-sm border-r-2 border-b-2 border-muted-foreground/40 opacity-60 hover:opacity-100"
      onPointerDown={handlePointerDown}
    />
  );
}

function clamp(value: number, min: number, max: number): number {
  return Math.min(max, Math.max(min, value));
}
