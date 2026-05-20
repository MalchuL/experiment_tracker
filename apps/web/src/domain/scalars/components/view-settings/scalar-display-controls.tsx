"use client";

import { Label } from "@/components/ui/label";
import { Slider } from "@/components/ui/slider";
import type { SyncMode } from "@/domain/scalars/types";

interface ScalarDisplayControlsProps {
  syncMode: SyncMode;
  setSyncMode: (mode: SyncMode) => void;
  soloMode: boolean;
  onToggleSoloMode: () => void;
  cardHeight: number;
  setCardHeight: (value: number) => void;
  cardMinWidth: number;
  setCardMinWidth: (value: number) => void;
  hoverNameMaxLength: number;
  setHoverNameMaxLength: (value: number) => void;
  smoothing: number;
  onSmoothingChange: (value: number[]) => void;
  onSmoothingCommit: (value: number[]) => void;
  maxPointsPerPlot: number;
  maxArtifactStepsPerObject: number;
  dotThreshold: number;
}

export function ScalarDisplayControls({
  syncMode,
  setSyncMode,
  soloMode,
  onToggleSoloMode,
  cardHeight,
  setCardHeight,
  cardMinWidth,
  setCardMinWidth,
  hoverNameMaxLength,
  setHoverNameMaxLength,
  smoothing,
  onSmoothingChange,
  onSmoothingCommit,
  maxPointsPerPlot,
  maxArtifactStepsPerObject,
  dotThreshold,
}: ScalarDisplayControlsProps) {
  return (
    <div className="space-y-2">
      <div className="space-y-1.5">
        <Label className="text-xs">Sync mode</Label>
        <select
          value={syncMode}
          onChange={(event) => setSyncMode(event.target.value as SyncMode)}
          className="h-8 w-full rounded border border-border bg-background px-2 text-xs text-foreground"
          data-testid="select-sync-mode"
        >
          <option value="all">All axes</option>
          <option value="x-only">X axis only</option>
          <option value="y-only">Y axis only</option>
          <option value="independent">Independent</option>
        </select>
      </div>

      <div>
        <button
          type="button"
          onClick={onToggleSoloMode}
          className={`h-8 w-full rounded border px-2 text-xs ${
            soloMode ? "border-primary bg-primary text-primary-foreground" : "border-border"
          }`}
          data-testid="button-solo-mode"
        >
          {soloMode ? "Solo on" : "Solo off"}
        </button>
      </div>

      <SliderRow
        label="Card height"
        value={cardHeight}
        suffix="px"
        min={320}
        max={1120}
        step={20}
        onChange={setCardHeight}
        testId="slider-card-size"
      />
      <SliderRow
        label="Card width"
        value={cardMinWidth}
        suffix="px"
        min={480}
        max={1520}
        step={40}
        onChange={setCardMinWidth}
        testId="slider-card-width"
      />
      <SliderRow
        label="Hover name"
        value={hoverNameMaxLength}
        suffix=" chars"
        min={10}
        max={250}
        step={5}
        onChange={setHoverNameMaxLength}
        testId="slider-hover-name-length"
      />
      <div className="space-y-1.5">
        <div className="flex items-center justify-between">
          <Label className="text-xs">Smoothing</Label>
          <span className="font-mono text-xs">{smoothing.toFixed(2)}</span>
        </div>
        <Slider
          value={[smoothing]}
          onValueChange={onSmoothingChange}
          onValueCommit={onSmoothingCommit}
          min={0}
          max={0.99}
          step={0.01}
          data-testid="slider-smoothing"
        />
      </div>
      <p className="text-[11px] leading-4 text-muted-foreground">
        Each plot requests up to {maxPointsPerPlot.toLocaleString()} points per experiment and scalar.
        Artifact sliders request up to {maxArtifactStepsPerObject.toLocaleString()} steps per object.
        Series with {dotThreshold} points or fewer show markers.
      </p>
    </div>
  );
}

function SliderRow({
  label,
  value,
  suffix,
  min,
  max,
  step,
  onChange,
  testId,
}: {
  label: string;
  value: number;
  suffix: string;
  min: number;
  max: number;
  step: number;
  onChange: (value: number) => void;
  testId: string;
}) {
  return (
    <div className="space-y-1.5">
      <div className="flex items-center justify-between">
        <Label className="text-xs">{label}</Label>
        <span className="font-mono text-xs">
          {value}
          {suffix}
        </span>
      </div>
      <Slider
        value={[value]}
        onValueChange={(next) => onChange(next[0])}
        min={min}
        max={max}
        step={step}
        data-testid={testId}
      />
    </div>
  );
}
