/**
 * Max metric rows rendered on a single experiment card in the project DAG view
 * (`project-dag-view.tsx`). Additional tracked metrics still load for the experiment;
 * the card shows a “+N more” line when over this cap.
 *
 * In-app docs: `/docs/reference/dag-view`.
 */
export const DAG_NODE_MAX_DISPLAY_METRICS = 20;

/**
 * Fixed width (px) of each experiment card in the DAG. Must stay in sync with
 * `calculateDagTreeLayout` in `calculate-dag-layout.ts` so subtree layout matches rendered nodes.
 */
export const DAG_NODE_WIDTH_PX = 240;

/** Minimum width for user-resizable DAG cards. */
export const DAG_NODE_MIN_WIDTH_PX = 160;

/**
 * Vertical footprint (px) used by the DAG tree layout for stacking children below parents.
 * Matches the approximate rendered card height used in layout math.
 */
export const DAG_NODE_HEIGHT_PX = 100;
