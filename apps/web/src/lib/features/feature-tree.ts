export type FeatureNode = {
  name: string;
  children?: FeatureNode[];
};

export type FeatureDiffStatus = "unchanged" | "added" | "removed" | "renamed" | "changed";

export type FeatureDiffNode = {
  key: string;
  status: FeatureDiffStatus;
  parent?: FeatureNode;
  child?: FeatureNode;
  children: FeatureDiffNode[];
};

export function isFeatureNodeArray(value: unknown): value is FeatureNode[] {
  return (
    Array.isArray(value) &&
    value.every((node) => isFeatureNode(node))
  );
}

function isFeatureNode(value: unknown): value is FeatureNode {
  if (typeof value !== "object" || value === null) return false;
  const node = value as { name?: unknown; children?: unknown };
  if (typeof node.name !== "string" || node.name.trim() === "") return false;
  return node.children == null || isFeatureNodeArray(node.children);
}

export function parseFeatureNodes(value: unknown): FeatureNode[] {
  return isFeatureNodeArray(value) ? normalizeFeatureNodes(value) : [];
}

export function parseFeatureNodesJson(json: string): FeatureNode[] {
  const parsed = JSON.parse(json) as unknown;
  if (!isFeatureNodeArray(parsed)) {
    throw new Error("Features must be a JSON array of { name, children? } nodes.");
  }
  return normalizeFeatureNodes(parsed);
}

export function formatFeatureNodesJson(features: FeatureNode[]): string {
  return JSON.stringify(features, null, 2);
}

export function featureNodesToTreeText(features: FeatureNode[]): string {
  if (features.length === 0) return "(no features)";
  const lines: string[] = [];
  const visit = (nodes: FeatureNode[], depth: number) => {
    for (const node of nodes) {
      lines.push(`${"  ".repeat(depth)}- ${node.name}`);
      if (node.children?.length) visit(node.children, depth + 1);
    }
  };
  visit(features, 0);
  return lines.join("\n");
}

export function diffFeatureTrees(parentFeatures: FeatureNode[], childFeatures: FeatureNode[]) {
  return diffFeatureSiblings(parentFeatures, childFeatures, "root");
}

function diffFeatureSiblings(
  parentFeatures: FeatureNode[],
  childFeatures: FeatureNode[],
  keyPrefix: string
): FeatureDiffNode[] {
  const childUsed = new Set<number>();
  const matchedRows: Array<{ parentIndex: number; childIndex: number; row: FeatureDiffNode }> = [];
  const removedRows: Array<{ parentIndex: number; row: FeatureDiffNode }> = [];

  parentFeatures.forEach((parent, parentIndex) => {
    const childIndex = findBestChildMatch(parent, childFeatures, childUsed);
    if (childIndex === -1) {
      removedRows.push({
        parentIndex,
        row: {
          key: `${keyPrefix}:removed:${parentIndex}:${parent.name}`,
          status: "removed",
          parent,
          children: [],
        },
      });
      return;
    }

    childUsed.add(childIndex);
    const child = childFeatures[childIndex];
    const children = diffFeatureSiblings(
      parent.children ?? [],
      child.children ?? [],
      `${keyPrefix}:${parentIndex}:${childIndex}`
    );
    const renamed = parent.name !== child.name;
    matchedRows.push({
      parentIndex,
      childIndex,
      row: {
        key: `${keyPrefix}:matched:${parentIndex}:${childIndex}:${parent.name}:${child.name}`,
        status: renamed ? "renamed" : "unchanged",
        parent,
        child,
        children,
      },
    });
  });

  const rows: FeatureDiffNode[] = [];
  const matchedRowsByChildIndex = new Map(matchedRows.map((match) => [match.childIndex, match]));
  const pushedRemovedRows = new Set<number>();

  childFeatures.forEach((child, childIndex) => {
    const matchedRow = matchedRowsByChildIndex.get(childIndex);
    if (matchedRow) {
      removedRows.forEach((removedRow) => {
        if (pushedRemovedRows.has(removedRow.parentIndex)) return;
        if (removedRow.parentIndex > matchedRow.parentIndex) return;
        rows.push(removedRow.row);
        pushedRemovedRows.add(removedRow.parentIndex);
      });
      rows.push(matchedRow.row);
      return;
    }

    rows.push({
      key: `${keyPrefix}:added:${childIndex}:${child.name}`,
      status: "added",
      child,
      children: featureBranchToDiffNodes(child.children ?? [], "added", `${keyPrefix}:added:${childIndex}`),
    });
  });

  removedRows.forEach((removedRow) => {
    if (pushedRemovedRows.has(removedRow.parentIndex)) return;
    rows.push(removedRow.row);
  });

  return rows;
}

function featureBranchToDiffNodes(
  features: FeatureNode[],
  status: Extract<FeatureDiffStatus, "added" | "removed">,
  keyPrefix: string
): FeatureDiffNode[] {
  return features.map((feature, index) => ({
    key: `${keyPrefix}:${status}:${index}:${feature.name}`,
    status,
    ...(status === "added" ? { child: feature } : { parent: feature }),
    children: featureBranchToDiffNodes(feature.children ?? [], status, `${keyPrefix}:${index}`),
  }));
}

function findBestChildMatch(
  parent: FeatureNode,
  childFeatures: FeatureNode[],
  childUsed: Set<number>
): number {
  const exactIndex = childFeatures.findIndex(
    (child, index) => !childUsed.has(index) && normalizeName(child.name) === normalizeName(parent.name)
  );
  if (exactIndex !== -1) return exactIndex;

  let bestIndex = -1;
  let bestDistance = Number.POSITIVE_INFINITY;
  childFeatures.forEach((child, index) => {
    if (childUsed.has(index)) return;
    const distance = levenshteinDistance(normalizeName(parent.name), normalizeName(child.name));
    if (distance < bestDistance) {
      bestDistance = distance;
      bestIndex = index;
    }
  });

  const maxLength = Math.max(parent.name.length, bestIndex === -1 ? 0 : childFeatures[bestIndex].name.length);
  const threshold = Math.max(2, Math.floor(maxLength * 0.35));
  return bestDistance <= threshold ? bestIndex : -1;
}

function normalizeName(name: string): string {
  return name.trim().toLowerCase();
}

function normalizeFeatureNodes(features: FeatureNode[]): FeatureNode[] {
  return features.map((feature) => ({
    name: feature.name,
    ...(feature.children?.length
      ? { children: normalizeFeatureNodes(feature.children) }
      : {}),
  }));
}

function levenshteinDistance(a: string, b: string): number {
  const previous = Array.from({ length: b.length + 1 }, (_, index) => index);
  const current = Array.from({ length: b.length + 1 }, () => 0);

  for (let i = 1; i <= a.length; i++) {
    current[0] = i;
    for (let j = 1; j <= b.length; j++) {
      const substitutionCost = a[i - 1] === b[j - 1] ? 0 : 1;
      current[j] = Math.min(
        previous[j] + 1,
        current[j - 1] + 1,
        previous[j - 1] + substitutionCost
      );
    }
    for (let j = 0; j <= b.length; j++) previous[j] = current[j];
  }

  return previous[b.length];
}
