"use client";

import { useState } from "react";
import { ArrowRight, ChevronRight, Copy } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  ExperimentDiffIcon,
  experimentDiffSurfaceClass,
  type ExperimentDiffStatus,
} from "@/components/shared/experiment-diff-ui";
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from "@/components/ui/collapsible";
import { jsonPath } from "@/domain/experiments/lib/hparams-json";
import type { HparamsDocument, JsonValue } from "@/domain/experiments/types";
import { useToast } from "@/lib/hooks/use-toast";
import { cn } from "@/lib/utils";

type DiffStatus = ExperimentDiffStatus;

export function ExperimentHparamsTree({
  hparams,
  parentHparams = null,
  showDiffs = false,
}: {
  hparams: HparamsDocument;
  parentHparams?: HparamsDocument | null;
  showDiffs?: boolean;
}) {
  const entries = showDiffs && parentHparams
    ? unionKeys(parentHparams, hparams)
    : Object.keys(hparams);

  if (entries.length === 0) {
    return <pre className="rounded-md border bg-muted/20 p-3 text-xs">{"{}"}</pre>;
  }

  return (
    <div className="min-w-0 overflow-hidden rounded-md border bg-muted/10 font-mono text-xs">
      {entries.map((key) => (
        <JsonNode
          key={key}
          name={key}
          currentValue={hparams[key]}
          parentValue={parentHparams?.[key]}
          currentPresent={Object.hasOwn(hparams, key)}
          parentPresent={parentHparams ? Object.hasOwn(parentHparams, key) : false}
          path={[key]}
          depth={0}
          showDiffs={showDiffs && parentHparams !== null}
        />
      ))}
    </div>
  );
}

function JsonNode({
  name,
  currentValue,
  parentValue,
  currentPresent,
  parentPresent,
  path,
  depth,
  showDiffs,
}: {
  name: string;
  currentValue: JsonValue | undefined;
  parentValue: JsonValue | undefined;
  currentPresent: boolean;
  parentPresent: boolean;
  path: (string | number)[];
  depth: number;
  showDiffs: boolean;
}) {
  const { toast } = useToast();
  const [open, setOpen] = useState(depth < 1);
  const displayedValue = currentPresent ? currentValue : parentValue;
  const isContainer = isJsonContainer(displayedValue);
  const status = getStatus(currentValue, parentValue, currentPresent, parentPresent);
  const keys = showDiffs && isJsonContainer(parentValue) && isJsonContainer(currentValue)
    ? unionKeys(parentValue, currentValue)
    : isJsonContainer(displayedValue)
      ? Object.keys(displayedValue)
      : [];

  const copy = async (text: string, label: string) => {
    try {
      await navigator.clipboard.writeText(text);
      toast({ title: `${label} copied` });
    } catch {
      toast({ title: `Failed to copy ${label.toLowerCase()}`, variant: "destructive" });
    }
  };

  const row = (
    <div
      className={cn(
        "group flex min-w-0 items-center gap-1.5 border-b border-border/35 py-1.5 pr-1 hover:bg-muted/30",
        showDiffs && experimentDiffSurfaceClass(status)
      )}
      style={{ paddingLeft: `${8 + depth * 14}px` }}
    >
      {isContainer ? (
        <ChevronRight className={cn("h-3.5 w-3.5 shrink-0 transition-transform", open && "rotate-90")} />
      ) : (
        <span className="h-3.5 w-3.5 shrink-0" />
      )}
      {showDiffs ? <DiffIcon status={status} /> : null}
      <span className={cn("min-w-0 break-all text-foreground", status === "removed" && "line-through text-muted-foreground")}>
        {name}
      </span>
      {!isContainer ? (
        <ValueDiff
          currentValue={currentValue}
          parentValue={parentValue}
          currentPresent={currentPresent}
          status={showDiffs ? status : "unchanged"}
        />
      ) : null}
      <span className="ml-auto flex shrink-0 opacity-0 group-hover:opacity-100 group-focus-within:opacity-100">
        <Button
          type="button"
          variant="ghost"
          size="icon"
          className="h-6 w-6"
          aria-label={`Copy path ${jsonPath(path)}`}
          onClick={(event) => {
            event.stopPropagation();
            void copy(jsonPath(path), "Path");
          }}
        >
          <Copy className="h-3 w-3" />
        </Button>
        <Button
          type="button"
          variant="ghost"
          size="icon"
          className="h-6 w-6"
          aria-label={`Copy value ${jsonPath(path)}`}
          onClick={(event) => {
            event.stopPropagation();
            void copy(JSON.stringify(displayedValue), "Value");
          }}
        >
          <Copy className="h-3 w-3" />
        </Button>
      </span>
    </div>
  );

  if (!isContainer) return row;
  return (
    <Collapsible open={open} onOpenChange={setOpen}>
      <CollapsibleTrigger asChild>{row}</CollapsibleTrigger>
      <CollapsibleContent>
        {keys.map((key) => {
          const arrayKey = Array.isArray(displayedValue) ? Number(key) : key;
          const currentContainer = isJsonContainer(currentValue) ? currentValue : undefined;
          const parentContainer = isJsonContainer(parentValue) ? parentValue : undefined;
          return (
            <JsonNode
              key={key}
              name={Array.isArray(displayedValue) ? `[${key}]` : key}
              currentValue={currentContainer?.[arrayKey as never]}
              parentValue={parentContainer?.[arrayKey as never]}
              currentPresent={currentContainer ? Object.hasOwn(currentContainer, arrayKey) : false}
              parentPresent={parentContainer ? Object.hasOwn(parentContainer, arrayKey) : false}
              path={[...path, arrayKey]}
              depth={depth + 1}
              showDiffs={showDiffs}
            />
          );
        })}
      </CollapsibleContent>
    </Collapsible>
  );
}

function ValueDiff({
  currentValue,
  parentValue,
  currentPresent,
  status,
}: {
  currentValue: JsonValue | undefined;
  parentValue: JsonValue | undefined;
  currentPresent: boolean;
  status: DiffStatus;
}) {
  if (status === "changed") {
    return (
      <span className="flex min-w-0 items-center gap-1 text-muted-foreground">
        <span className="break-all line-through">{displayValue(parentValue)}</span>
        <ArrowRight className="h-3 w-3 shrink-0" />
        <span className="break-all text-foreground">{displayValue(currentValue)}</span>
      </span>
    );
  }
  return (
    <span className={cn("min-w-0 break-all text-muted-foreground", status === "removed" && "line-through")}>
      = {displayValue(currentPresent ? currentValue : parentValue)}
    </span>
  );
}

function DiffIcon({ status }: { status: DiffStatus }) {
  return <span className="flex w-3.5 shrink-0 items-center justify-center"><ExperimentDiffIcon status={status} /></span>;
}

function getStatus(
  currentValue: JsonValue | undefined,
  parentValue: JsonValue | undefined,
  currentPresent: boolean,
  parentPresent: boolean
): DiffStatus {
  if (!parentPresent) return "added";
  if (!currentPresent) return "removed";
  if (isJsonContainer(currentValue) && isJsonContainer(parentValue)) return "unchanged";
  return JSON.stringify(currentValue) === JSON.stringify(parentValue) ? "unchanged" : "changed";
}

function unionKeys(parent: JsonValue[] | HparamsDocument, current: JsonValue[] | HparamsDocument): string[] {
  return Array.from(new Set([...Object.keys(parent), ...Object.keys(current)]));
}

function isJsonContainer(value: JsonValue | undefined): value is JsonValue[] | HparamsDocument {
  return value !== null && typeof value === "object";
}

function displayValue(value: JsonValue | undefined): string {
  if (typeof value === "string") return JSON.stringify(value);
  return String(value);
}
