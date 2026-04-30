import type { Edge } from "@xyflow/react";
import { MarkerType } from "@xyflow/react";
import type { Experiment } from "../types";

export type SavedPositions = Record<string, { x: number; y: number }>;

export interface DagLayoutComputed {
  positionsById: Record<string, { x: number; y: number }>;
  edges: Edge[];
}

const NODE_WIDTH = 220;
const NODE_HEIGHT = 100;
const HORIZONTAL_SPACING = 36;
const VERTICAL_SPACING = 72;

/** Extra Y shift for nodes without a saved position (appears below tree-computed slot). */
const NEW_NODE_BOTTOM_OFFSET = 40;

/**
 * Tree layout (subtree width) with optional saved positions per node, matching
 * third-party ExperimentGraph calculateLayout.
 */
export function calculateDagTreeLayout(
  experiments: Experiment[],
  savedPositions: SavedPositions
): DagLayoutComputed {
  const experimentMap = new Map(experiments.map((e) => [e.id, e]));

  const childrenMap = new Map<string, Experiment[]>();
  const roots: Experiment[] = [];

  for (const exp of experiments) {
    const pid = exp.parentExperimentId;
    if (pid && experimentMap.has(pid)) {
      const ch = childrenMap.get(pid) ?? [];
      ch.push(exp);
      childrenMap.set(pid, ch);
    } else {
      roots.push(exp);
    }
  }

  const positionsById: Record<string, { x: number; y: number }> = {};

  function getSubtreeWidth(exp: Experiment): number {
    const children = childrenMap.get(exp.id) ?? [];
    if (children.length === 0) return NODE_WIDTH;
    return children.reduce(
      (sum, child) => sum + getSubtreeWidth(child) + HORIZONTAL_SPACING,
      -HORIZONTAL_SPACING
    );
  }

  function layoutTree(exp: Experiment, x: number, y: number) {
    const saved = savedPositions[exp.id];
    const position = saved ?? { x, y: y + NEW_NODE_BOTTOM_OFFSET };
    positionsById[exp.id] = position;

    const children = childrenMap.get(exp.id) ?? [];
    if (children.length > 0) {
      const totalWidth = children.reduce(
        (sum, child) => sum + getSubtreeWidth(child) + HORIZONTAL_SPACING,
        -HORIZONTAL_SPACING
      );
      let currentX = x - totalWidth / 2 + NODE_WIDTH / 2;

      children.forEach((child) => {
        const childWidth = getSubtreeWidth(child);
        layoutTree(
          child,
          currentX + childWidth / 2 - NODE_WIDTH / 2,
          y + NODE_HEIGHT + VERTICAL_SPACING
        );
        currentX += childWidth + HORIZONTAL_SPACING;
      });
    }
  }

  let startX = 0;
  roots.forEach((root) => {
    const width = getSubtreeWidth(root);
    layoutTree(root, startX + width / 2, 0);
    startX += width + HORIZONTAL_SPACING * 2;
  });

  const edges: Edge[] = experiments
    .filter((exp) => exp.parentExperimentId && experimentMap.has(exp.parentExperimentId))
    .map((exp) => ({
      id: `${exp.parentExperimentId}-${exp.id}`,
      source: exp.parentExperimentId!,
      target: exp.id,
      type: "smoothstep",
      animated: exp.status === "running",
      markerEnd: {
        type: MarkerType.ArrowClosed,
        markerUnits: "userSpaceOnUse",
        width: 11,
        height: 11,
      },
      style: { stroke: exp.color ?? "hsl(var(--border))" },
    }));

  return { positionsById, edges };
}
