# DAG view: metrics on nodes

The project **DAG** (`DAG View` in the sidebar) draws each experiment as a card in a lineage graph. Tracked metrics that are included in the project’s **display metrics** list can show on that card with values and deltas vs the parent run.

## How many metrics fit on one card

The UI renders at most **`DAG_NODE_MAX_DISPLAY_METRICS`** metric rows per node. If more metrics apply to that experiment, the card still lists the first rows in **display-metric order**, then a small **“+N more”** hint for the remainder.

| What | Path |
|------|------|
| **Cap (change this)** | `apps/web/src/lib/constants/dag.ts` → `DAG_NODE_MAX_DISPLAY_METRICS` |
| Card layout & “+N more” | `apps/web/src/domain/experiments/components/project-dag-view.tsx` (`ExperimentNode`) |

Restart the Next.js dev server after editing the constant so the client bundle picks up the new value.

:::note
This limit is **only** how many rows fit on the graph card. It does not change which metrics exist on the experiment or how [metric value formatting](/docs/reference/metric-display-formatting) prints each number.
:::

## Card width and layout height

Each experiment node uses a fixed **width** so columns of metrics line up; the tree layout (`calculate-dag-tree-layout`) uses the same width so edges and sibling spacing stay aligned. **Height** is the vertical footprint assumed when placing the next row of children.

| What | Path |
|------|------|
| **Width & height (change these)** | `apps/web/src/lib/constants/dag.ts` → `DAG_NODE_WIDTH_PX`, `DAG_NODE_HEIGHT_PX` |
| Card shell | `apps/web/src/domain/experiments/components/project-dag-view.tsx` (`ExperimentNode`) |
| Subtree / Y positions | `apps/web/src/domain/experiments/dag/calculate-dag-layout.ts` (`calculateDagTreeLayout`) |

Edit **`DAG_NODE_WIDTH_PX`** (and **`DAG_NODE_HEIGHT_PX`** if needed) when you want a wider or narrower card; keep layout and CSS on the same numbers.

## Related

- [Metric display: precision & thresholds](/docs/reference/metric-display-formatting) — number formatting in tables, DAG cells, and sidebars.
- [Callouts, details & formatting](/docs/reference/doc-features) — Markdown blocks used across these docs.
