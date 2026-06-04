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
