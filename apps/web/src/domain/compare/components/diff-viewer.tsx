"use client";

import { type Ref, useMemo, useRef, useState } from "react";
import { ChevronsDown, ChevronsUp, ChevronDown, ChevronUp, UnfoldVertical } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { ScrollArea } from "@/components/ui/scroll-area";
import { cn } from "@/lib/utils";
import { computeDiff, getDiffStats, type DiffLine } from "../lib/diff";
import { getLanguageFromExtension } from "../lib/file-tree";
import { ExpandUnchangedControl } from "./expand-unchanged-control";
import { InlineDiffText } from "./inline-diff-text";

const COLLAPSED_CONTEXT_LINES = 3;
const PARTIAL_EXPAND_LINES = 10;

interface DiffViewerProps {
  oldContent: string;
  newContent: string;
  oldFileName?: string;
  newFileName?: string;
  oldExtension?: string;
  newExtension?: string;
}

type VisibleDiffRow =
  | { type: "line"; line: DiffLine; originalIndex: number }
  | { type: "collapsed"; firstIndex: number; count: number };

type NavigationState = {
  oldContent: string;
  newContent: string;
  index: number;
} | null;

type HighlightState = {
  oldContent: string;
  newContent: string;
  lineIndex: number;
} | null;

type ExpandedRangeState = {
  oldContent: string;
  newContent: string;
  ranges: Array<{ start: number; end: number }>;
} | null;

export function DiffViewer({
  oldContent,
  newContent,
  oldFileName = "Original",
  newFileName = "Modified",
  oldExtension,
  newExtension,
}: DiffViewerProps) {
  const [expandUnchanged, setExpandUnchanged] = useState(false);
  const [navigation, setNavigation] = useState<NavigationState>(null);
  const [highlight, setHighlight] = useState<HighlightState>(null);
  const [expandedRanges, setExpandedRanges] = useState<ExpandedRangeState>(null);
  const lineRefs = useRef(new Map<number, HTMLDivElement>());

  const diff = useMemo(() => computeDiff(oldContent, newContent), [oldContent, newContent]);
  const stats = useMemo(() => getDiffStats(diff), [diff]);
  const oldLanguage = getLanguageFromExtension(oldExtension ?? oldFileName.split(".").pop());
  const newLanguage = getLanguageFromExtension(newExtension ?? newFileName.split(".").pop());
  const expandedLineIndexes = useMemo(
    () => toExpandedLineIndexes(expandedRanges, oldContent, newContent),
    [expandedRanges, newContent, oldContent]
  );
  const changeLineIndexes = useMemo(
    () => diff.map((line, index) => (line.type === "unchanged" ? -1 : index)).filter((index) => index !== -1),
    [diff]
  );
  const hasChanges = changeLineIndexes.length > 0;
  const visibleRows = useMemo(
    () =>
      !hasChanges || expandUnchanged
        ? toFullDiffRows(diff)
        : toCollapsedDiffRows(diff, expandedLineIndexes),
    [diff, expandUnchanged, expandedLineIndexes, hasChanges]
  );
  const activeChangeIndex =
    navigation?.oldContent === oldContent &&
    navigation.newContent === newContent &&
    navigation.index >= 0 &&
    navigation.index < changeLineIndexes.length
      ? navigation.index
      : -1;
  const activeChangeNumber =
    activeChangeIndex >= 0 && activeChangeIndex < changeLineIndexes.length
      ? activeChangeIndex + 1
      : 0;
  const highlightedLineIndex =
    highlight?.oldContent === oldContent && highlight.newContent === newContent
      ? highlight.lineIndex
      : null;

  const moveToChange = (direction: "previous" | "next") => {
    if (changeLineIndexes.length === 0) {
      return;
    }

    const currentIndex =
      activeChangeIndex >= 0 && activeChangeIndex < changeLineIndexes.length
        ? activeChangeIndex
        : -1;
    const nextChangeIndex =
      direction === "next"
        ? currentIndex < changeLineIndexes.length - 1
          ? currentIndex + 1
          : 0
        : currentIndex > 0
          ? currentIndex - 1
          : changeLineIndexes.length - 1;
    const lineIndex = changeLineIndexes[nextChangeIndex];

    setNavigation({ oldContent, newContent, index: nextChangeIndex });
    setHighlight({ oldContent, newContent, lineIndex });
    requestAnimationFrame(() => {
      lineRefs.current.get(lineIndex)?.scrollIntoView({ block: "center", behavior: "smooth" });
    });
    window.setTimeout(() => {
      setHighlight((current) =>
        current?.oldContent === oldContent &&
        current.newContent === newContent &&
        current.lineIndex === lineIndex
          ? null
          : current
      );
    }, 1200);
  };

  const expandHiddenRange = (start: number, end: number) => {
    setExpandedRanges((current) => {
      const currentRanges =
        current?.oldContent === oldContent && current.newContent === newContent
          ? current.ranges
          : [];
      return {
        oldContent,
        newContent,
        ranges: mergeRanges([...currentRanges, { start, end }]),
      };
    });
  };

  return (
    <div className="flex h-full flex-col">
      <div className="flex flex-wrap items-center gap-x-4 gap-y-2 border-b bg-muted/30 px-4 py-2">
        <div className="flex min-w-0 flex-wrap items-center gap-x-3 gap-y-2">
          <div className="min-w-0 truncate text-sm">
            <span className="font-medium">Comparing: </span>
            <span className="text-muted-foreground">{oldFileName}</span>
            <span className="px-2 text-muted-foreground">/</span>
            <span className="text-muted-foreground">{newFileName}</span>
          </div>
          <div className="flex shrink-0 flex-nowrap items-center gap-2">
            {stats.changes === 0 ? (
              <Badge variant="outline" className="text-muted-foreground">
                Files equal
              </Badge>
            ) : (
              <>
                <Badge variant="outline" className="border-green-500/20 bg-green-500/10 text-green-600">
                  +{stats.additions}
                </Badge>
                <Badge variant="outline" className="border-red-500/20 bg-red-500/10 text-red-600">
                  -{stats.deletions}
                </Badge>
              </>
            )}
          </div>
        </div>
        <div className="ml-auto flex shrink-0 flex-wrap items-center justify-end gap-x-4 gap-y-2">
          <ExpandUnchangedControl
            id="compare-expand-unchanged-lines"
            expanded={expandUnchanged}
            onExpandedChange={setExpandUnchanged}
            disabled={!hasChanges}
          />
          <div className="flex items-center gap-1">
            <Button
              type="button"
              variant="ghost"
              size="icon"
              className="h-8 w-8"
              disabled={changeLineIndexes.length === 0}
              onClick={() => moveToChange("previous")}
              aria-label="Go to previous change"
              title="Previous change"
            >
              <ChevronUp className="h-4 w-4" />
            </Button>
            <Button
              type="button"
              variant="ghost"
              size="icon"
              className="h-8 w-8"
              disabled={changeLineIndexes.length === 0}
              onClick={() => moveToChange("next")}
              aria-label="Go to next change"
              title="Next change"
            >
              <ChevronDown className="h-4 w-4" />
            </Button>
            <span className="min-w-12 text-center text-xs tabular-nums text-muted-foreground">
              {activeChangeNumber}/{changeLineIndexes.length}
            </span>
          </div>
        </div>
      </div>
      <ScrollArea className="flex-1">
        <div className="min-w-max font-mono text-sm">
          {visibleRows.map((row) =>
            row.type === "collapsed" ? (
              <CollapsedDiffRows
                key={`collapsed-${row.firstIndex}`}
                firstIndex={row.firstIndex}
                count={row.count}
                onExpandRange={expandHiddenRange}
              />
            ) : (
              <DiffLineRow
                key={row.originalIndex}
                rowRef={(node) => {
                  if (node) {
                    lineRefs.current.set(row.originalIndex, node);
                  } else {
                    lineRefs.current.delete(row.originalIndex);
                  }
                }}
                line={row.line}
                previousLine={diff[row.originalIndex - 1]}
                nextLine={diff[row.originalIndex + 1]}
                oldLanguage={oldLanguage}
                newLanguage={newLanguage}
                highlighted={highlightedLineIndex === row.originalIndex}
              />
            )
          )}
        </div>
      </ScrollArea>
    </div>
  );
}

function toFullDiffRows(diff: DiffLine[]): VisibleDiffRow[] {
  return diff.map((line, originalIndex) => ({ type: "line", line, originalIndex }));
}

function toExpandedLineIndexes(
  expandedRanges: ExpandedRangeState,
  oldContent: string,
  newContent: string
): Set<number> {
  const indexes = new Set<number>();
  if (expandedRanges?.oldContent !== oldContent || expandedRanges.newContent !== newContent) {
    return indexes;
  }

  expandedRanges.ranges.forEach((range) => {
    for (let index = range.start; index <= range.end; index += 1) {
      indexes.add(index);
    }
  });
  return indexes;
}

function mergeRanges(ranges: Array<{ start: number; end: number }>) {
  const sortedRanges = ranges
    .map((range) => ({
      start: Math.min(range.start, range.end),
      end: Math.max(range.start, range.end),
    }))
    .sort((a, b) => a.start - b.start);
  const mergedRanges: Array<{ start: number; end: number }> = [];

  sortedRanges.forEach((range) => {
    const previousRange = mergedRanges[mergedRanges.length - 1];
    if (!previousRange || range.start > previousRange.end + 1) {
      mergedRanges.push(range);
      return;
    }
    previousRange.end = Math.max(previousRange.end, range.end);
  });

  return mergedRanges;
}

function toCollapsedDiffRows(diff: DiffLine[], expandedLineIndexes: Set<number>): VisibleDiffRow[] {
  if (!diff.some((line) => line.type !== "unchanged")) {
    return toFullDiffRows(diff);
  }

  const visibleLineIndexes = new Set<number>();
  diff.forEach((line, index) => {
    if (line.type === "unchanged") {
      return;
    }

    const start = Math.max(0, index - COLLAPSED_CONTEXT_LINES);
    const end = Math.min(diff.length - 1, index + COLLAPSED_CONTEXT_LINES);
    for (let visibleIndex = start; visibleIndex <= end; visibleIndex += 1) {
      visibleLineIndexes.add(visibleIndex);
    }
  });
  expandedLineIndexes.forEach((index) => visibleLineIndexes.add(index));

  const rows: VisibleDiffRow[] = [];
  let index = 0;
  while (index < diff.length) {
    if (visibleLineIndexes.has(index)) {
      rows.push({ type: "line", line: diff[index], originalIndex: index });
      index += 1;
      continue;
    }

    const firstIndex = index;
    while (index < diff.length && !visibleLineIndexes.has(index)) {
      index += 1;
    }
    rows.push({ type: "collapsed", firstIndex, count: index - firstIndex });
  }

  return rows;
}

function CollapsedDiffRows({
  firstIndex,
  count,
  onExpandRange,
}: {
  firstIndex: number;
  count: number;
  onExpandRange: (start: number, end: number) => void;
}) {
  const lastIndex = firstIndex + count - 1;
  const firstSliceEnd = Math.min(lastIndex, firstIndex + PARTIAL_EXPAND_LINES - 1);
  const lastSliceStart = Math.max(firstIndex, lastIndex - PARTIAL_EXPAND_LINES + 1);
  const canExpandPartially = count > PARTIAL_EXPAND_LINES;

  return (
    <div className="compare-diff-collapsed flex items-center gap-3 px-4 py-1 text-xs">
      <div className="flex items-center gap-1">
        <Button
          type="button"
          variant="ghost"
          size="sm"
          className="compare-diff-collapsed-btn"
          onClick={() => onExpandRange(firstIndex, lastIndex)}
          aria-label="Show all hidden unchanged lines in this block"
          title="Show all hidden lines"
        >
          <UnfoldVertical className="h-3.5 w-3.5" />
          All
        </Button>
        {canExpandPartially && (
          <Button
            type="button"
            variant="ghost"
            size="sm"
            className="compare-diff-collapsed-btn"
            onClick={() => onExpandRange(firstIndex, firstSliceEnd)}
            aria-label={`Show first ${PARTIAL_EXPAND_LINES} hidden unchanged lines`}
            title={`Show first ${PARTIAL_EXPAND_LINES} hidden lines`}
          >
            <ChevronsDown className="h-3.5 w-3.5" />
            Top
          </Button>
        )}
        {canExpandPartially && (
          <Button
            type="button"
            variant="ghost"
            size="sm"
            className="compare-diff-collapsed-btn"
            onClick={() => onExpandRange(lastSliceStart, lastIndex)}
            aria-label={`Show last ${PARTIAL_EXPAND_LINES} hidden unchanged lines`}
            title={`Show last ${PARTIAL_EXPAND_LINES} hidden lines`}
          >
            <ChevronsUp className="h-3.5 w-3.5" />
            Bottom
          </Button>
        )}
      </div>
      <span>
        {count} unchanged {count === 1 ? "line" : "lines"} hidden
      </span>
    </div>
  );
}

const DiffLineRow = ({
  line,
  previousLine,
  nextLine,
  oldLanguage,
  newLanguage,
  highlighted,
  rowRef,
}: {
  line: DiffLine;
  previousLine?: DiffLine;
  nextLine?: DiffLine;
  oldLanguage: string;
  newLanguage: string;
  highlighted: boolean;
  rowRef: Ref<HTMLDivElement>;
}) => {
  const bgColor = {
    add: "bg-green-500/10 hover:bg-green-500/15",
    remove: "bg-red-500/10 hover:bg-red-500/15",
    unchanged: "hover:bg-accent/30",
  }[line.type];
  const indicator = { add: "+", remove: "-", unchanged: " " }[line.type];
  const indicatorColor = {
    add: "text-green-600",
    remove: "text-red-600",
    unchanged: "text-transparent",
  }[line.type];
  const compareWith =
    line.type === "remove" && nextLine?.type === "add"
      ? nextLine.content
      : line.type === "add" && previousLine?.type === "remove"
        ? previousLine.content
        : undefined;

  return (
    <div
      ref={rowRef}
      className={cn(
        "flex gap-3 px-4 py-0.5 transition-[background-color,box-shadow] duration-300",
        bgColor,
        highlighted && "bg-yellow-400/25 shadow-[inset_3px_0_0_hsl(var(--primary))]"
      )}
    >
      <div className="flex shrink-0 select-none gap-3">
        <span className="w-8 text-right text-muted-foreground/50">
          {line.lineNumber.old || ""}
        </span>
        <span className="w-8 text-right text-muted-foreground/50">
          {line.lineNumber.new || ""}
        </span>
        <span className={cn("w-4", indicatorColor)}>{indicator}</span>
      </div>
      <InlineDiffText
        content={line.content}
        compareWith={compareWith}
        side={line.type === "remove" ? "old" : "new"}
        language={line.type === "remove" ? oldLanguage : newLanguage}
        className="flex-1 text-foreground/85"
      />
    </div>
  );
};
