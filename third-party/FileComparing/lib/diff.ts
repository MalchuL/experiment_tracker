export interface DiffLine {
  type: 'add' | 'remove' | 'unchanged';
  content: string;
  lineNumber: {
    old?: number;
    new?: number;
  };
}

/**
 * Simple diff algorithm for comparing two strings
 */
export function computeDiff(oldContent: string, newContent: string): DiffLine[] {
  const oldLines = oldContent.split('\n');
  const newLines = newContent.split('\n');
  
  const diff: DiffLine[] = [];
  let oldIndex = 0;
  let newIndex = 0;

  while (oldIndex < oldLines.length || newIndex < newLines.length) {
    const oldLine = oldLines[oldIndex];
    const newLine = newLines[newIndex];

    if (oldIndex >= oldLines.length) {
      // Only new lines remain
      diff.push({
        type: 'add',
        content: newLine,
        lineNumber: { new: newIndex + 1 },
      });
      newIndex++;
    } else if (newIndex >= newLines.length) {
      // Only old lines remain
      diff.push({
        type: 'remove',
        content: oldLine,
        lineNumber: { old: oldIndex + 1 },
      });
      oldIndex++;
    } else if (oldLine === newLine) {
      // Lines are the same
      diff.push({
        type: 'unchanged',
        content: oldLine,
        lineNumber: { old: oldIndex + 1, new: newIndex + 1 },
      });
      oldIndex++;
      newIndex++;
    } else {
      // Lines are different - try to find if it's an add or remove
      const nextOldMatch = newLines.slice(newIndex).findIndex((line) => line === oldLine);
      const nextNewMatch = oldLines.slice(oldIndex).findIndex((line) => line === newLine);

      if (nextNewMatch !== -1 && (nextOldMatch === -1 || nextNewMatch < nextOldMatch)) {
        // Old line removed
        diff.push({
          type: 'remove',
          content: oldLine,
          lineNumber: { old: oldIndex + 1 },
        });
        oldIndex++;
      } else if (nextOldMatch !== -1) {
        // New line added
        diff.push({
          type: 'add',
          content: newLine,
          lineNumber: { new: newIndex + 1 },
        });
        newIndex++;
      } else {
        // Both lines changed
        diff.push({
          type: 'remove',
          content: oldLine,
          lineNumber: { old: oldIndex + 1 },
        });
        diff.push({
          type: 'add',
          content: newLine,
          lineNumber: { new: newIndex + 1 },
        });
        oldIndex++;
        newIndex++;
      }
    }
  }

  return diff;
}

/**
 * Get diff statistics
 */
export function getDiffStats(diff: DiffLine[]): {
  additions: number;
  deletions: number;
  changes: number;
} {
  let additions = 0;
  let deletions = 0;

  diff.forEach((line) => {
    if (line.type === 'add') additions++;
    if (line.type === 'remove') deletions++;
  });

  return {
    additions,
    deletions,
    changes: additions + deletions,
  };
}
