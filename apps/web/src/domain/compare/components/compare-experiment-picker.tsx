"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { ChevronDown } from "lucide-react";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import type { Experiment } from "@/domain/experiments/types";
import { experimentMatchesSearch } from "@/domain/experiments/lib/experiment-matches-search";
import { cn } from "@/lib/utils";

export function CompareExperimentPicker({
  experiments,
  isLoading = false,
  onSelect,
  placeholder = "Add experiment",
  disabledExperimentIds = [],
  value = null,
  includeNone = false,
  noneLabel = "No comparison",
  noneValue = "__none",
  label,
  triggerClassName,
}: {
  experiments: Experiment[];
  isLoading?: boolean;
  onSelect: (experimentId: string) => void;
  placeholder?: string;
  disabledExperimentIds?: string[];
  value?: string | null;
  includeNone?: boolean;
  noneLabel?: string;
  noneValue?: string;
  label?: string;
  triggerClassName?: string;
}) {
  const [open, setOpen] = useState(false);
  const [searchQuery, setSearchQuery] = useState("");
  const searchInputRef = useRef<HTMLInputElement>(null);
  const disabledIds = useMemo(() => new Set(disabledExperimentIds), [disabledExperimentIds]);

  useEffect(() => {
    if (!open) {
      setSearchQuery("");
      return;
    }
    requestAnimationFrame(() => searchInputRef.current?.focus());
  }, [open]);

  const filteredExperiments = useMemo(() => {
    return experiments.filter((experiment) => experimentMatchesSearch(experiment, searchQuery));
  }, [experiments, searchQuery]);

  const selectedExperiment =
    value && value !== noneValue
      ? experiments.find((experiment) => experiment.id === value)
      : undefined;

  const triggerContent =
    value === noneValue && includeNone ? (
      <span>{noneLabel}</span>
    ) : selectedExperiment ? (
      <ExperimentPickerOption experiment={selectedExperiment} />
    ) : (
      <span className="text-muted-foreground">{isLoading ? "Loading experiments..." : placeholder}</span>
    );

  const picker = (
    <DropdownMenu open={open} onOpenChange={setOpen}>
      <DropdownMenuTrigger asChild>
        <button
          type="button"
          className={cn(
            "flex h-10 w-full min-w-0 items-center justify-between gap-2 rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50",
            triggerClassName
          )}
          disabled={isLoading}
        >
          <span className="min-w-0 flex-1 truncate text-left">{triggerContent}</span>
          <ChevronDown className="h-4 w-4 shrink-0 opacity-50" aria-hidden />
        </button>
      </DropdownMenuTrigger>
      <DropdownMenuContent
        className="flex max-h-[min(24rem,calc(100dvh-2rem))] w-[min(24rem,var(--radix-dropdown-menu-trigger-width))] flex-col overflow-hidden p-0"
        align="start"
        sideOffset={4}
        onCloseAutoFocus={(e) => e.preventDefault()}
      >
        <div
          className="shrink-0 border-b border-border p-2"
          onPointerDown={(e) => {
            if (e.target instanceof HTMLInputElement) {
              return;
            }
            e.preventDefault();
            searchInputRef.current?.focus();
          }}
        >
          <Input
            ref={searchInputRef}
            type="search"
            placeholder="Search by name, id, or description…"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="h-9"
            aria-label="Search experiments"
            autoComplete="off"
            onKeyDown={(e) => e.stopPropagation()}
            onPointerDown={(e) => e.stopPropagation()}
          />
        </div>
        <div className="max-h-[min(20rem,calc(100dvh-7rem))] min-h-0 flex-1 overflow-y-auto overscroll-contain p-1 [scrollbar-gutter:stable]">
          {isLoading ? (
            <div className="space-y-2 p-2">
              <Skeleton className="h-9 w-full" />
              <Skeleton className="h-9 w-full" />
              <Skeleton className="h-9 w-full" />
            </div>
          ) : experiments.length === 0 ? (
            <p className="px-2 py-3 text-sm text-muted-foreground">No experiments in this project</p>
          ) : (
            <>
              {includeNone &&
              (searchQuery.trim() === "" || noneLabel.toLowerCase().includes(searchQuery.trim().toLowerCase())) ? (
                <DropdownMenuItem className="cursor-pointer" onSelect={() => onSelect(noneValue)}>
                  {noneLabel}
                </DropdownMenuItem>
              ) : null}
              {filteredExperiments.length === 0 ? (
                <p className="px-2 py-3 text-sm text-muted-foreground">No experiments match your search</p>
              ) : (
                filteredExperiments.map((experiment) => (
                  <DropdownMenuItem
                    key={experiment.id}
                    className="cursor-pointer"
                    disabled={disabledIds.has(experiment.id)}
                    onSelect={() => onSelect(experiment.id)}
                  >
                    <ExperimentPickerOption experiment={experiment} />
                  </DropdownMenuItem>
                ))
              )}
            </>
          )}
        </div>
      </DropdownMenuContent>
    </DropdownMenu>
  );

  if (label) {
    return (
      <label className="flex min-w-0 items-center gap-2 text-sm">
        <span className="shrink-0 text-muted-foreground">{label}</span>
        {picker}
      </label>
    );
  }

  return picker;
}

function ExperimentPickerOption({ experiment }: { experiment: Pick<Experiment, "name" | "color"> }) {
  return (
    <span className="inline-flex min-w-0 items-center gap-2">
      <span
        className="h-2.5 w-2.5 shrink-0 rounded-full"
        style={{ backgroundColor: experiment.color || "#3b82f6" }}
      />
      <span className="min-w-0 truncate">{experiment.name}</span>
    </span>
  );
}
