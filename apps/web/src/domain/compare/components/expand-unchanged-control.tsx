"use client";

import { CompareLabeledSwitch } from "./compare-labeled-switch";

const EXPAND_UNCHANGED_TIP =
  "When on, every line is shown. When off, unchanged regions between edits are collapsed (identical files always show in full).";

interface ExpandUnchangedControlProps {
  id: string;
  expanded: boolean;
  onExpandedChange: (expanded: boolean) => void;
  disabled?: boolean;
}

export function ExpandUnchangedControl({
  id,
  expanded,
  onExpandedChange,
  disabled = false,
}: ExpandUnchangedControlProps) {
  return (
    <CompareLabeledSwitch
      id={id}
      label="Expand unchanged"
      checked={expanded}
      onCheckedChange={onExpandedChange}
      disabled={disabled}
      tip={EXPAND_UNCHANGED_TIP}
      ariaLabel="Expand unchanged lines in the diff view"
    />
  );
}
