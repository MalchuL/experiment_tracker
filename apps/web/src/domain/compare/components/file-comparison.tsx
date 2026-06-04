"use client";

import { type Ref, useMemo, useRef, useState } from "react";
import { ChevronsDown, ChevronsUp, ChevronDown, ChevronUp, File, GitCompare, UnfoldVertical } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Checkbox } from "@/components/ui/checkbox";
import { ScrollArea } from "@/components/ui/scroll-area";
import { cn } from "@/lib/utils";
import { getLanguageFromExtension } from "../lib/file-tree";
import { InlineDiffText } from "./inline-diff-text";

const COLLAPSED_CONTEXT_LINES = 3;
const PARTIAL_EXPAND_LINES = 10;

interface ComparedFile {
  path: string;
  content: string;
  extension?: string;
}

interface FileComparisonProps {
  leftFile: ComparedFile;
  rightFile: ComparedFile;
  className?: string;
}

type SideBySideDiffLine = {
  type: "same" | "added" | "removed" | "changed";
  leftLineNumber?: number;
  rightLineNumber?: number;
  leftContent?: string;
  rightContent?: string;
};

type VisibleComparisonRow =
  | { type: "line"; line: SideBySideDiffLine; originalIndex: number }
  | { type: "collapsed"; firstIndex: number; count: number };

type NavigationState = {
  leftContent: string;
  rightContent: string;
  index: number;
} | null;

type HighlightState = {
  leftContent: string;
  rightContent: string;
  lineIndex: number;
} | null;

type ExpandedRangeState = {
  leftContent: string;
  rightContent: string;
  ranges: Array<{ start: number; end: number }>;
} | null;

function computeSimpleDiff(leftLines: string[], rightLines: string[]): SideBySideDiffLine[] {
  const result: SideBySideDiffLine[] = [];
  const maxLines = Math.max(leftLines.length, rightLines.length);

  for (let index = 0; index < maxLines; index += 1) {
    const leftLine = leftLines[index];
    const rightLine = rightLines[index];

    if (leftLine === undefined && rightLine !== undefined) {
      result.push({
        type: "added",
        rightLineNumber: index + 1,
        rightContent: rightLine,
      });
    } else if (leftLine !== undefined && rightLine === undefined) {
      result.push({
        type: "removed",
        leftLineNumber: index + 1,
        leftContent: leftLine,
      });
    } else if (leftLine === rightLine) {
      result.push({
        type: "same",
        leftLineNumber: index + 1,
        rightLineNumber: index + 1,
        leftContent: leftLine,
        rightContent: rightLine,
      });
    } else {
      result.push({
        type: "changed",
        leftLineNumber: index + 1,
        rightLineNumber: index + 1,
        leftContent: leftLine,
        rightContent: rightLine,
      });
    }
  }

  return result;
}

export function FileComparison({ leftFile, rightFile, className }: FileComparisonProps) {
  const [showUnchanged, setShowUnchanged] = useState(false);
  const [navigation, setNavigation] = useState<NavigationState>(null);
  const [highlight, setHighlight] = useState<HighlightState>(null);
  const [expandedRanges, setExpandedRanges] = useState<ExpandedRangeState>(null);
  const rowRefs = useRef(new Map<number, HTMLDivElement>());

  const leftLines = useMemo(() => leftFile.content.split("\n"), [leftFile.content]);
  const rightLines = useMemo(() => rightFile.content.split("\n"), [rightFile.content]);
  const diff = useMemo(() => computeSimpleDiff(leftLines, rightLines), [leftLines, rightLines]);
  const leftFileName = leftFile.path.split("/").pop() || leftFile.path;
  const rightFileName = rightFile.path.split("/").pop() || rightFile.path;
  const leftLanguage = getLanguageFromExtension(leftFile.extension ?? leftFileName.split(".").pop());
  const rightLanguage = getLanguageFromExtension(rightFile.extension ?? rightFileName.split(".").pop());
  const expandedLineIndexes = useMemo(
    () => toExpandedLineIndexes(expandedRanges, leftFile.content, rightFile.content),
    [expandedRanges, leftFile.content, rightFile.content]
  );
  const visibleRows = useMemo(
    () => (showUnchanged ? toFullComparisonRows(diff) : toCollapsedComparisonRows(diff, expandedLineIndexes)),
    [diff, expandedLineIndexes, showUnchanged]
  );
  const stats = useMemo(
    () => ({
      added: diff.filter((line) => line.type === "added").length,
      removed: diff.filter((line) => line.type === "removed").length,
      changed: diff.filter((line) => line.type === "changed").length,
    }),
    [diff]
  );
  const changeLineIndexes = useMemo(
    () => diff.map((line, index) => (line.type === "same" ? -1 : index)).filter((index) => index !== -1),
    [diff]
  );
  const activeChangeIndex =
    navigation?.leftContent === leftFile.content &&
    navigation.rightContent === rightFile.content &&
    navigation.index >= 0 &&
    navigation.index < changeLineIndexes.length
      ? navigation.index
      : -1;
  const activeChangeNumber =
    activeChangeIndex >= 0 && activeChangeIndex < changeLineIndexes.length
      ? activeChangeIndex + 1
      : 0;
  const highlightedLineIndex =
    highlight?.leftContent === leftFile.content && highlight.rightContent === rightFile.content
      ? highlight.lineIndex
      : null;
  const hasChanges = stats.added > 0 || stats.removed > 0 || stats.changed > 0;

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

    setNavigation({ leftContent: leftFile.content, rightContent: rightFile.content, index: nextChangeIndex });
    setHighlight({ leftContent: leftFile.content, rightContent: rightFile.content, lineIndex });
    requestAnimationFrame(() => {
      rowRefs.current.get(lineIndex)?.scrollIntoView({ block: "center", behavior: "smooth" });
    });
    window.setTimeout(() => {
      setHighlight((current) =>
        current?.leftContent === leftFile.content &&
        current.rightContent === rightFile.content &&
        current.lineIndex === lineIndex
          ? null
          : current
      );
    }, 1200);
  };

  const expandHiddenRange = (start: number, end: number) => {
    setExpandedRanges((current) => {
      const currentRanges =
        current?.leftContent === leftFile.content && current.rightContent === rightFile.content
          ? current.ranges
          : [];
      return {
        leftContent: leftFile.content,
        rightContent: rightFile.content,
        ranges: mergeRanges([...currentRanges, { start, end }]),
      };
    });
  };

  return (
    <Card className={cn("flex h-full flex-col overflow-hidden rounded-none border-0", className)}>
      <div className="border-b bg-muted/30 px-4 py-3">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div className="flex items-center gap-2">
            <GitCompare className="h-4 w-4 text-muted-foreground" />
            <span className="text-sm font-semibold">File Comparison</span>
          </div>
          <div className="flex shrink-0 items-center gap-3">
            <label
              htmlFor="side-by-side-show-unchanged-lines"
              className="flex cursor-pointer select-none items-center gap-2 text-sm text-muted-foreground"
            >
              <Checkbox
                id="side-by-side-show-unchanged-lines"
                checked={showUnchanged}
                onCheckedChange={(value) => setShowUnchanged(value === true)}
              />
              <span>Show unchanged</span>
            </label>
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
        <div className="mt-2 flex items-center gap-3 text-xs">
          {!hasChanges ? (
            <Badge variant="outline" className="text-muted-foreground">
              Files equal
            </Badge>
          ) : (
            <>
              {stats.added > 0 && (
                <Badge variant="outline" className="border-green-500/20 bg-green-500/10 text-green-600">
                  +{stats.added} added
                </Badge>
              )}
              {stats.removed > 0 && (
                <Badge variant="outline" className="border-red-500/20 bg-red-500/10 text-red-600">
                  -{stats.removed} removed
                </Badge>
              )}
              {stats.changed > 0 && (
                <Badge variant="outline" className="border-yellow-500/20 bg-yellow-500/10 text-yellow-600">
                  ~{stats.changed} changed
                </Badge>
              )}
            </>
          )}
        </div>
      </div>

      <div className="grid grid-cols-2 border-b">
        <FileNameHeader fileName={leftFileName} className="border-r" />
        <FileNameHeader fileName={rightFileName} />
      </div>

      <ScrollArea className="flex-1">
        <div className="font-mono text-sm">
          {visibleRows.map((row) =>
            row.type === "collapsed" ? (
              <CollapsedComparisonRows
                key={`collapsed-${row.firstIndex}`}
                firstIndex={row.firstIndex}
                count={row.count}
                onExpandRange={expandHiddenRange}
              />
            ) : (
              <SideBySideDiffRow
                key={row.originalIndex}
                rowRef={(node) => {
                  if (node) {
                    rowRefs.current.set(row.originalIndex, node);
                  } else {
                    rowRefs.current.delete(row.originalIndex);
                  }
                }}
                line={row.line}
                leftLanguage={leftLanguage}
                rightLanguage={rightLanguage}
                highlighted={highlightedLineIndex === row.originalIndex}
              />
            )
          )}
          {visibleRows.length === 0 && (
            <div className="flex h-32 items-center justify-center px-4 text-sm text-muted-foreground">
              No changed lines. Enable unchanged lines to inspect the full file.
            </div>
          )}
        </div>
      </ScrollArea>
    </Card>
  );
}

function toFullComparisonRows(diff: SideBySideDiffLine[]): VisibleComparisonRow[] {
  return diff.map((line, originalIndex) => ({ type: "line", line, originalIndex }));
}

function toExpandedLineIndexes(
  expandedRanges: ExpandedRangeState,
  leftContent: string,
  rightContent: string
): Set<number> {
  const indexes = new Set<number>();
  if (expandedRanges?.leftContent !== leftContent || expandedRanges.rightContent !== rightContent) {
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

function toCollapsedComparisonRows(
  diff: SideBySideDiffLine[],
  expandedLineIndexes: Set<number>
): VisibleComparisonRow[] {
  if (!diff.some((line) => line.type !== "same")) {
    return [];
  }

  const visibleLineIndexes = new Set<number>();
  diff.forEach((line, index) => {
    if (line.type === "same") {
      return;
    }

    const start = Math.max(0, index - COLLAPSED_CONTEXT_LINES);
    const end = Math.min(diff.length - 1, index + COLLAPSED_CONTEXT_LINES);
    for (let visibleIndex = start; visibleIndex <= end; visibleIndex += 1) {
      visibleLineIndexes.add(visibleIndex);
    }
  });
  expandedLineIndexes.forEach((index) => visibleLineIndexes.add(index));

  const rows: VisibleComparisonRow[] = [];
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

function FileNameHeader({ fileName, className }: { fileName: string; className?: string }) {
  return (
    <div className={cn("flex items-center gap-2 bg-muted/20 px-4 py-2", className)}>
      <File className="h-4 w-4 text-muted-foreground" />
      <span className="min-w-0 truncate text-sm font-medium">{fileName}</span>
    </div>
  );
}

function CollapsedComparisonRows({
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
    <div className="grid grid-cols-2 border-y bg-muted/25 text-xs text-muted-foreground">
      <div className="col-span-2 flex items-center gap-3 px-4 py-1">
        <div className="flex shrink-0 select-none gap-3">
          <span className="w-8" />
          <span className="w-4 text-center">...</span>
        </div>
        <span>{count} unchanged {count === 1 ? "line" : "lines"} hidden</span>
        <div className="ml-2 flex items-center gap-1">
          {canExpandPartially && (
            <Button
              type="button"
              variant="ghost"
              size="sm"
              className="h-7 px-2 text-xs"
              onClick={() => onExpandRange(firstIndex, firstSliceEnd)}
              aria-label={`Show first ${PARTIAL_EXPAND_LINES} hidden unchanged lines`}
              title={`Show first ${PARTIAL_EXPAND_LINES} hidden lines`}
            >
              <ChevronsDown className="h-3.5 w-3.5" />
              Top
            </Button>
          )}
          <Button
            type="button"
            variant="ghost"
            size="sm"
            className="h-7 px-2 text-xs"
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
              className="h-7 px-2 text-xs"
              onClick={() => onExpandRange(lastSliceStart, lastIndex)}
              aria-label={`Show last ${PARTIAL_EXPAND_LINES} hidden unchanged lines`}
              title={`Show last ${PARTIAL_EXPAND_LINES} hidden lines`}
            >
              <ChevronsUp className="h-3.5 w-3.5" />
              Bottom
            </Button>
          )}
        </div>
      </div>
    </div>
  );
}

function SideBySideDiffRow({
  line,
  leftLanguage,
  rightLanguage,
  highlighted,
  rowRef,
}: {
  line: SideBySideDiffLine;
  leftLanguage: string;
  rightLanguage: string;
  highlighted: boolean;
  rowRef: Ref<HTMLDivElement>;
}) {
  const bgClass = {
    added: "bg-green-500/10",
    removed: "bg-red-500/10",
    changed: "bg-yellow-500/10",
    same: "",
  }[line.type];

  return (
    <div
      ref={rowRef}
      className={cn(
        "grid grid-cols-2 transition-[background-color,box-shadow] duration-300 hover:bg-accent/20",
        bgClass,
        highlighted && "bg-yellow-400/25 shadow-[inset_3px_0_0_hsl(var(--primary))]"
      )}
    >
      <DiffCell
        lineNumber={line.leftLineNumber}
        content={line.leftContent}
        compareWith={line.type === "changed" ? line.rightContent : undefined}
        side="old"
        language={leftLanguage}
        className="border-r"
      />
      <DiffCell
        lineNumber={line.rightLineNumber}
        content={line.rightContent}
        compareWith={line.type === "changed" ? line.leftContent : undefined}
        side="new"
        language={rightLanguage}
      />
    </div>
  );
}

function DiffCell({
  lineNumber,
  content,
  compareWith,
  side,
  language,
  className,
}: {
  lineNumber?: number;
  content?: string;
  compareWith?: string;
  side: "old" | "new";
  language?: string;
  className?: string;
}) {
  return (
    <div className={cn("flex min-w-0", className)}>
      <div className="sticky left-0 min-w-12 select-none border-r bg-muted/20 px-3 py-1 text-right text-xs text-muted-foreground/60">
        {lineNumber || ""}
      </div>
      <div className="min-w-0 flex-1 px-3 py-1">
        <InlineDiffText content={content} compareWith={compareWith} side={side} language={language} />
      </div>
    </div>
  );
}
