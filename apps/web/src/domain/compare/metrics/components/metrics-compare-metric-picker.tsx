"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { Input } from "@/components/ui/input";
import { formatMetricLabel, projectMetricKeyString } from "@/lib/metrics/format-metric-label";
import type { SelectiveMetricKey } from "@/domain/metrics/types";
import type { MetricNameOption } from "../types/metrics-compare";

type MetricsCompareMetricPickerProps = {
  options: MetricNameOption[];
  excludedKeys?: Set<string>;
  onSelect: (option: MetricNameOption) => void;
  placeholder?: string;
};

export function MetricsCompareMetricPicker({
  options,
  excludedKeys,
  onSelect,
  placeholder = "Search metrics…",
}: MetricsCompareMetricPickerProps) {
  const [query, setQuery] = useState("");
  const [open, setOpen] = useState(false);
  const rootRef = useRef<HTMLDivElement>(null);

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    return options.filter((option) => {
      const key = projectMetricKeyString(option);
      if (excludedKeys?.has(key)) return false;
      if (!q) return true;
      return option.displayName.toLowerCase().includes(q);
    });
  }, [options, excludedKeys, query]);

  useEffect(() => {
    if (!open) return;
    const onPointerDown = (event: PointerEvent) => {
      const root = rootRef.current;
      if (!root) return;
      const target = event.target;
      if (target instanceof Node && root.contains(target)) return;
      setOpen(false);
    };
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") setOpen(false);
    };
    document.addEventListener("pointerdown", onPointerDown, true);
    document.addEventListener("keydown", onKeyDown, true);
    return () => {
      document.removeEventListener("pointerdown", onPointerDown, true);
      document.removeEventListener("keydown", onKeyDown, true);
    };
  }, [open]);

  return (
    <div ref={rootRef} className="relative">
      <Input
        placeholder={placeholder}
        value={query}
        aria-expanded={open}
        aria-haspopup="listbox"
        autoComplete="off"
        onChange={(event) => {
          setQuery(event.target.value);
          setOpen(true);
        }}
        onClick={() => setOpen(true)}
        onFocus={() => setOpen(true)}
        className="h-8 text-sm"
      />
      {open ? (
        <div
          className="absolute left-0 right-0 top-full z-50 mt-1 overflow-hidden rounded-md border border-border bg-popover text-popover-foreground shadow-md"
          role="listbox"
        >
          <div className="max-h-48 overflow-y-auto p-1 text-sm">
            {filtered.length > 0 ? (
              filtered.map((option) => (
                <button
                  key={projectMetricKeyString(option)}
                  type="button"
                  role="option"
                  className="w-full rounded-sm px-2 py-1.5 text-left hover:bg-accent"
                  onMouseDown={(event) => event.preventDefault()}
                  onClick={() => {
                    onSelect(option);
                    setQuery("");
                    setOpen(false);
                  }}
                >
                  {option.displayName}
                </button>
              ))
            ) : (
              <p className="px-2 py-2 text-muted-foreground">
                {query.trim() ? "No matching metrics." : "No metrics available."}
              </p>
            )}
          </div>
        </div>
      ) : null}
    </div>
  );
}

export function uniqueDimensionsToOptions(
  items: SelectiveMetricKey[]
): MetricNameOption[] {
  return [...items]
    .sort((a, b) =>
      formatMetricLabel(a.name, a.label).localeCompare(formatMetricLabel(b.name, b.label))
    )
    .map((key) => ({
      ...key,
      displayName: formatMetricLabel(key.name, key.label),
    }));
}
