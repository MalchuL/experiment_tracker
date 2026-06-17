"use client";

import { useState } from "react";
import { ChevronRight, Copy } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import {
  ExperimentDiffIcon,
  experimentDiffSurfaceClass,
  type ExperimentDiffStatus,
} from "@/components/shared/experiment-diff-ui";
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from "@/components/ui/collapsible";
import { jsonPath } from "@/domain/experiments/lib/hparams-json";
import {
  displayHparamsValue,
  hparamsValueClassName,
} from "@/domain/experiments/lib/hparams-display";
import type { HparamsDocument, JsonValue } from "@/domain/experiments/types";
import { useToast } from "@/lib/hooks/use-toast";
import { cn } from "@/lib/utils";

type DiffStatus = ExperimentDiffStatus;

const HPARAMS_TREE_INDENT_PX = 12;

const HPARAMS_TREE_ROOT_CLASS =
  "min-w-0 max-w-full overflow-hidden rounded-md border border-border/60 bg-muted/5 px-1 py-2 text-sm leading-[1.6]";

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
    return (
      <pre className="rounded-md border border-border/60 bg-muted/5 p-3 text-sm leading-[1.6] text-muted-foreground">
        {"{}"}
      </pre>
    );
  }

  return (
    <div className={HPARAMS_TREE_ROOT_CLASS}>
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
  const status = getStatus(currentValue, parentValue, currentPresent, parentPresent);
  const isExpandableContainer = isExpandableJsonContainer(displayedValue);
  const keys =
    showDiffs && isJsonContainer(parentValue) && isJsonContainer(currentValue)
      ? unionKeys(parentValue, currentValue)
      : isJsonContainer(displayedValue) && isExpandableContainer
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

  const showStackedValueDiff = showDiffs && !isExpandableContainer && status === "changed";
  const rowPaddingLeft = 4 + depth * HPARAMS_TREE_INDENT_PX;
  const hasDiffHighlight = showDiffs && status !== "unchanged";

  const row = (
    <div
      className={cn(
        "group relative flex w-full min-w-0 items-start gap-1.5 rounded-sm py-1.5 pr-7",
        showDiffs && experimentDiffSurfaceClass(status),
        !hasDiffHighlight && "hover:bg-muted/25"
      )}
      style={{ paddingLeft: rowPaddingLeft }}
    >
      <span className="flex w-3.5 shrink-0 items-center justify-center self-center">
        {isExpandableContainer ? (
          <ChevronRight
            className={cn(
              "h-3.5 w-3.5 text-muted-foreground transition-transform",
              open && "rotate-90"
            )}
          />
        ) : null}
      </span>
      {showDiffs ? (
        <span
          className={cn(
            "flex w-3.5 shrink-0 items-center justify-center",
            showStackedValueDiff && "pt-0.5"
          )}
        >
          <DiffIcon status={status} />
        </span>
      ) : null}
      <span
        className={cn(
          "min-w-0 max-w-[36%] shrink-0 break-words font-sans text-[13px] font-medium text-foreground/90",
          status === "removed" && "text-muted-foreground line-through"
        )}
      >
        {name}
      </span>
      {!isExpandableContainer ? (
        <ValueDiff
          currentValue={currentValue}
          parentValue={parentValue}
          currentPresent={currentPresent}
          status={showDiffs ? status : "unchanged"}
        />
      ) : null}
      <HparamsNodeCopyMenu
        path={path}
        displayedValue={displayedValue}
        isContainer={isJsonContainer(displayedValue)}
        onCopy={copy}
        className="absolute right-0 top-1 shrink-0 opacity-0 transition-opacity group-hover:opacity-100 group-focus-within:opacity-100"
      />
    </div>
  );

  if (!isExpandableContainer) return row;

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
              name={key}
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

function HparamsNodeCopyMenu({
  path,
  displayedValue,
  isContainer,
  onCopy,
  className,
}: {
  path: (string | number)[];
  displayedValue: JsonValue | undefined;
  isContainer: boolean;
  onCopy: (text: string, label: string) => void | Promise<void>;
  className?: string;
}) {
  const pathText = jsonPath(path);
  const valueText = JSON.stringify(displayedValue);
  const assignmentValueText = isContainer ? valueText : displayHparamsValue(displayedValue);
  const pathAssignmentText = `${pathText}: ${assignmentValueText}`;

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button
          type="button"
          variant="ghost"
          size="icon"
          className={cn("h-7 w-7 text-muted-foreground/50 hover:text-muted-foreground", className)}
          aria-label={`Copy options for ${pathText}`}
          onClick={(event) => event.stopPropagation()}
          onPointerDown={(event) => event.stopPropagation()}
        >
          <Copy className="h-3 w-3" />
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end" className="w-48" onClick={(event) => event.stopPropagation()}>
        <DropdownMenuItem onSelect={() => onCopy(valueText, "Value")}>Copy value</DropdownMenuItem>
        <DropdownMenuItem onSelect={() => onCopy(pathText, "Path")}>Copy path</DropdownMenuItem>
        <DropdownMenuItem onSelect={() => onCopy(pathAssignmentText, "Path: value")}>
          Copy path: value
        </DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
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
      <span className="flex min-w-0 flex-1 flex-col gap-1 text-muted-foreground">
        <span className="flex min-w-0 items-baseline gap-1.5">
          <span className="shrink-0 text-muted-foreground/60">:</span>
          <span className="min-w-0 flex-1 break-all [overflow-wrap:anywhere] line-through">
            {renderValue(parentValue)}
          </span>
        </span>
        <span className="flex min-w-0 items-baseline gap-1.5 text-foreground">
          <span className="shrink-0 text-muted-foreground/60">:</span>
          <span className="min-w-0 flex-1 break-all [overflow-wrap:anywhere]">
            {renderValue(currentValue)}
          </span>
        </span>
      </span>
    );
  }

  const value = currentPresent ? currentValue : parentValue;

  return (
    <span
      className={cn(
        "flex min-w-0 flex-1 items-baseline gap-1.5",
        status === "removed" && "text-muted-foreground line-through"
      )}
    >
      <span className="shrink-0 text-muted-foreground/60">:</span>
      <span className="min-w-0 flex-1 break-all [overflow-wrap:anywhere]">{renderValue(value)}</span>
    </span>
  );
}

function renderValue(value: JsonValue | undefined) {
  return <HparamsValueText value={value} />;
}

function HparamsValueText({ value }: { value: JsonValue | undefined }) {
  if (value === null || value === undefined) {
    return <span className={hparamsValueClassName(value)}>{displayHparamsValue(value)}</span>;
  }

  if (Array.isArray(value) && canInlineHparamsArray(value)) {
    return (
      <span className="font-mono text-[13px] font-normal">
        <span className="text-muted-foreground/35">[</span>
        {value.map((item, index) => (
          <span key={index}>
            {index > 0 ? <span className="text-muted-foreground/35">, </span> : null}
            <HparamsValueText value={item} />
          </span>
        ))}
        <span className="text-muted-foreground/35">]</span>
      </span>
    );
  }

  if (typeof value === "string") {
    return (
      <span className={hparamsValueClassName(value)}>
        <span className="text-muted-foreground/35">&quot;</span>
        {value}
        <span className="text-muted-foreground/35">&quot;</span>
      </span>
    );
  }

  return (
    <span className={cn(hparamsValueClassName(value), "text-[13px]")}>
      {displayHparamsValue(value)}
    </span>
  );
}

function DiffIcon({ status }: { status: DiffStatus }) {
  return <ExperimentDiffIcon status={status} />;
}

function getStatus(
  currentValue: JsonValue | undefined,
  parentValue: JsonValue | undefined,
  currentPresent: boolean,
  parentPresent: boolean
): DiffStatus {
  if (!parentPresent) return "added";
  if (!currentPresent) return "removed";
  return JSON.stringify(currentValue) === JSON.stringify(parentValue) ? "unchanged" : "changed";
}

function unionKeys(parent: JsonValue[] | HparamsDocument, current: JsonValue[] | HparamsDocument): string[] {
  return Array.from(new Set([...Object.keys(parent), ...Object.keys(current)]));
}

function isExpandableJsonContainer(value: JsonValue | undefined): boolean {
  if (!isJsonContainer(value)) return false;
  if (Array.isArray(value)) return !canInlineHparamsArray(value);
  return Object.keys(value).length > 0;
}

function isJsonContainer(value: JsonValue | undefined): value is JsonValue[] | HparamsDocument {
  return value !== null && typeof value === "object";
}

function canInlineHparamsArray(value: JsonValue[]): boolean {
  if (value.length > 8) return false;
  return value.every((item) => !isJsonContainer(item));
}
