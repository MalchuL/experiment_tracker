"use client";

import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { cn } from "@/lib/utils";

interface CompareLabeledSwitchProps {
  id: string;
  label: string;
  checked: boolean;
  onCheckedChange: (checked: boolean) => void;
  disabled?: boolean;
  tip?: string;
  ariaLabel?: string;
}

export function CompareLabeledSwitch({
  id,
  label,
  checked,
  onCheckedChange,
  disabled = false,
  tip,
  ariaLabel,
}: CompareLabeledSwitchProps) {
  const control = (
    <div
      className={cn(
        "flex h-8 shrink-0 items-center gap-2",
        disabled && "opacity-60"
      )}
    >
      <Label
        htmlFor={id}
        className={cn(
          "text-sm font-normal",
          disabled ? "cursor-not-allowed text-muted-foreground/60" : "cursor-pointer"
        )}
      >
        {label}
      </Label>
      <Switch
        id={id}
        checked={checked}
        disabled={disabled}
        onCheckedChange={onCheckedChange}
        aria-label={ariaLabel ?? label}
      />
    </div>
  );

  if (!tip) {
    return control;
  }

  return (
    <TooltipProvider delayDuration={250}>
      <Tooltip>
        <TooltipTrigger asChild>{control}</TooltipTrigger>
        <TooltipContent side="bottom" className="max-w-xs">
          {tip}
        </TooltipContent>
      </Tooltip>
    </TooltipProvider>
  );
}
