import {
  DAG_NODE_HEIGHT_PX,
  DAG_NODE_WIDTH_PX,
} from "@/lib/constants/dag";

export type DagNodeRect = {
  x: number;
  y: number;
  width: number;
  height: number;
};

const DAG_NODE_COLLISION_GAP_PX = 16;
const DAG_NODE_PLACEMENT_SCAN_COLS = 12;
const DAG_NODE_PLACEMENT_MAX_ATTEMPTS = 120;

export function dagNodeRectsIntersect(a: DagNodeRect, b: DagNodeRect, gap = DAG_NODE_COLLISION_GAP_PX): boolean {
  return !(
    a.x + a.width + gap <= b.x ||
    b.x + b.width + gap <= a.x ||
    a.y + a.height + gap <= b.y ||
    b.y + b.height + gap <= a.y
  );
}

function toRect(
  position: { x: number; y: number },
  width = DAG_NODE_WIDTH_PX,
  height = DAG_NODE_HEIGHT_PX
): DagNodeRect {
  return { x: position.x, y: position.y, width, height };
}

/**
 * Nudges a candidate top-left until it no longer overlaps obstacle rects (fixed default size).
 * Scans right, then down in a grid from the tree-layout slot.
 */
export function findFreeDagNodePosition(
  candidate: { x: number; y: number },
  obstacles: DagNodeRect[],
  nodeWidth = DAG_NODE_WIDTH_PX,
  nodeHeight = DAG_NODE_HEIGHT_PX
): { x: number; y: number } {
  const stepX = nodeWidth + DAG_NODE_COLLISION_GAP_PX;
  const stepY = nodeHeight + DAG_NODE_COLLISION_GAP_PX;

  for (let attempt = 0; attempt < DAG_NODE_PLACEMENT_MAX_ATTEMPTS; attempt++) {
    const col = attempt % DAG_NODE_PLACEMENT_SCAN_COLS;
    const row = Math.floor(attempt / DAG_NODE_PLACEMENT_SCAN_COLS);
    const position = {
      x: candidate.x + col * stepX,
      y: candidate.y + row * stepY,
    };
    const rect = toRect(position, nodeWidth, nodeHeight);
    const intersects = obstacles.some((obstacle) => dagNodeRectsIntersect(rect, obstacle));
    if (!intersects) {
      return position;
    }
  }

  return candidate;
}

export function dagNodeRectFromPosition(
  position: { x: number; y: number },
  width = DAG_NODE_WIDTH_PX,
  height = DAG_NODE_HEIGHT_PX
): DagNodeRect {
  return toRect(position, width, height);
}
