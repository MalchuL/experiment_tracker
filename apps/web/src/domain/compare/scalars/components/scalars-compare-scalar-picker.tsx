"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { Input } from "@/components/ui/input";
import type { ScalarMetricOption } from "../types";

type ScalarsCompareScalarPickerProps = {
  options: ScalarMetricOption[];
  onSelect: (option: ScalarMetricOption) => void;
  placeholder?: string;
};

export function ScalarsCompareScalarPicker({
  options,
  onSelect,
  placeholder = "Search scalars...",
}: ScalarsCompareScalarPickerProps) {
  const [query, setQuery] = useState("");
  const [open, setOpen] = useState(false);
  const rootRef = useRef<HTMLDivElement>(null);

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) return options;
    return options.filter((option) => option.displayName.toLowerCase().includes(q));
  }, [options, query]);

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
                  key={option.name}
                  type="button"
                  role="option"
                  aria-selected={false}
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
                {query.trim() ? "No matching scalars." : "No scalars available."}
              </p>
            )}
          </div>
        </div>
      ) : null}
    </div>
  );
}
