"use client";

import { useEffect, useState } from "react";
import { LAST_LOGGED_POLL_INTERVAL_MS } from "@/lib/constants/live-refresh";
import { cn } from "@/lib/utils";

const INDICATOR_SIZE = 20;
const STROKE_WIDTH = 2;
const RADIUS = (INDICATOR_SIZE - STROKE_WIDTH) / 2;
const CIRCUMFERENCE = 2 * Math.PI * RADIUS;

interface LiveRefreshIndicatorProps {
  enabled: boolean;
  /** Timestamp (ms) when the current refresh cycle started — from poll or manual refresh. */
  cycleStartMs: number;
  onToggle: () => void;
  className?: string;
}

export function LiveRefreshIndicator({
  enabled,
  cycleStartMs,
  onToggle,
  className,
}: LiveRefreshIndicatorProps) {
  const [progress, setProgress] = useState(0);

  useEffect(() => {
    if (!enabled) {
      setProgress(0);
      return;
    }

    let frameId = 0;
    const tick = () => {
      const elapsed = Date.now() - cycleStartMs;
      setProgress(Math.min(1, elapsed / LAST_LOGGED_POLL_INTERVAL_MS));
      frameId = window.requestAnimationFrame(tick);
    };

    frameId = window.requestAnimationFrame(tick);
    return () => window.cancelAnimationFrame(frameId);
  }, [cycleStartMs, enabled]);

  const strokeDashoffset = CIRCUMFERENCE * (1 - progress);

  return (
    <button
      type="button"
      aria-label={enabled ? "Disable automatic refresh" : "Enable automatic refresh"}
      aria-pressed={enabled}
      title={enabled ? "Auto-refresh on — click to disable" : "Auto-refresh off — click to enable"}
      onClick={onToggle}
      className={cn(
        "inline-flex h-8 w-8 cursor-pointer items-center justify-center rounded-md text-muted-foreground transition-colors hover:bg-accent hover:text-foreground",
        !enabled && "opacity-60",
        className
      )}
      data-testid="button-live-refresh-indicator"
    >
      <svg
        width={INDICATOR_SIZE}
        height={INDICATOR_SIZE}
        viewBox={`0 0 ${INDICATOR_SIZE} ${INDICATOR_SIZE}`}
        className="-rotate-90"
        aria-hidden
      >
        <circle
          cx={INDICATOR_SIZE / 2}
          cy={INDICATOR_SIZE / 2}
          r={RADIUS}
          fill="none"
          stroke="currentColor"
          strokeOpacity={0.25}
          strokeWidth={STROKE_WIDTH}
        />
        {enabled ? (
          <circle
            cx={INDICATOR_SIZE / 2}
            cy={INDICATOR_SIZE / 2}
            r={RADIUS}
            fill="none"
            stroke="currentColor"
            strokeWidth={STROKE_WIDTH}
            strokeDasharray={CIRCUMFERENCE}
            strokeDashoffset={strokeDashoffset}
            strokeLinecap="round"
          />
        ) : null}
      </svg>
    </button>
  );
}
