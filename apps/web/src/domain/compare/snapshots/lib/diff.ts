export interface DiffLine {
  type: "add" | "remove" | "unchanged";
  content: string;
  lineNumber: {
    old?: number;
    new?: number;
  };
}

export function computeDiff(oldContent: string, newContent: string): DiffLine[] {
  const oldLines = oldContent.split("\n");
  const newLines = newContent.split("\n");
  const diff: DiffLine[] = [];
  let oldIndex = 0;
  let newIndex = 0;

  while (oldIndex < oldLines.length || newIndex < newLines.length) {
    const oldLine = oldLines[oldIndex];
    const newLine = newLines[newIndex];

    if (oldIndex >= oldLines.length) {
      diff.push({ type: "add", content: newLine, lineNumber: { new: newIndex + 1 } });
      newIndex += 1;
    } else if (newIndex >= newLines.length) {
      diff.push({ type: "remove", content: oldLine, lineNumber: { old: oldIndex + 1 } });
      oldIndex += 1;
    } else if (oldLine === newLine) {
      diff.push({
        type: "unchanged",
        content: oldLine,
        lineNumber: { old: oldIndex + 1, new: newIndex + 1 },
      });
      oldIndex += 1;
      newIndex += 1;
    } else {
      const nextOldMatch = newLines.slice(newIndex).findIndex((line) => line === oldLine);
      const nextNewMatch = oldLines.slice(oldIndex).findIndex((line) => line === newLine);

      if (nextNewMatch !== -1 && (nextOldMatch === -1 || nextNewMatch < nextOldMatch)) {
        diff.push({ type: "remove", content: oldLine, lineNumber: { old: oldIndex + 1 } });
        oldIndex += 1;
      } else if (nextOldMatch !== -1) {
        diff.push({ type: "add", content: newLine, lineNumber: { new: newIndex + 1 } });
        newIndex += 1;
      } else {
        diff.push({ type: "remove", content: oldLine, lineNumber: { old: oldIndex + 1 } });
        diff.push({ type: "add", content: newLine, lineNumber: { new: newIndex + 1 } });
        oldIndex += 1;
        newIndex += 1;
      }
    }
  }
  return diff;
}

export function getDiffStats(diff: DiffLine[]) {
  const additions = diff.filter((line) => line.type === "add").length;
  const deletions = diff.filter((line) => line.type === "remove").length;

  return {
    additions,
    deletions,
    changes: additions + deletions,
  };
}

export type SideBySideDiffLine = {
  type: "same" | "added" | "removed" | "changed";
  leftLineNumber?: number;
  rightLineNumber?: number;
  leftContent?: string;
  rightContent?: string;
};

export function computeSideBySideDiff(
  oldContent: string,
  newContent: string
): SideBySideDiffLine[] {
  const diff = computeDiff(oldContent, newContent);
  const result: SideBySideDiffLine[] = [];

  for (let index = 0; index < diff.length; index += 1) {
    const line = diff[index];

    if (line.type === "unchanged") {
      result.push({
        type: "same",
        leftLineNumber: line.lineNumber.old,
        rightLineNumber: line.lineNumber.new,
        leftContent: line.content,
        rightContent: line.content,
      });
      continue;
    }

    if (line.type === "remove") {
      const nextLine = diff[index + 1];
      if (nextLine?.type === "add") {
        result.push({
          type: "changed",
          leftLineNumber: line.lineNumber.old,
          rightLineNumber: nextLine.lineNumber.new,
          leftContent: line.content,
          rightContent: nextLine.content,
        });
        index += 1;
        continue;
      }

      result.push({
        type: "removed",
        leftLineNumber: line.lineNumber.old,
        leftContent: line.content,
      });
      continue;
    }

    result.push({
      type: "added",
      rightLineNumber: line.lineNumber.new,
      rightContent: line.content,
    });
  }

  return result;
}
