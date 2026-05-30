# Documentation content (`apps/web/content/docs/`)

- **Browse in the app**: open `/docs` in the web UI (workspace → Documentation).
- **Add or change pages**: follow **[Adding documentation pages](./contributing/adding-pages.md)** (manifest + markdown + build check).
- **Callouts & collapsible blocks**: see **[Callouts, details & formatting](./reference/doc-features.md)** and **[Common documentation patterns](./examples/common-patterns.md)**.
- **Extend the renderer** (directives, sanitize, components): **[Extending the docs pipeline](./contributing/extending-doc-pipeline.md)**.
- **Manifest**: [`../src/lib/docs/docs-manifest.ts`](../src/lib/docs/docs-manifest.ts) (`DOCS_MANIFEST`).
- **Admin panel (operators)**: [`reference/admin-panel.md`](./reference/admin-panel.md) → `/docs/reference/admin-panel`.
- **Metric UI formatting (precision / thresholds)**: [`reference/metric-display-formatting.md`](./reference/metric-display-formatting.md) → `/docs/reference/metric-display-formatting`.
- **DAG view (metrics per node)**: [`reference/dag-view.md`](./reference/dag-view.md) → `/docs/reference/dag-view`.
- **Routes**: Next.js catch-all [`../src/app/(core)/(workspace)/docs/[...path]/page.tsx`](../src/app/(core)/(workspace)/docs/[...path]/page.tsx).

Non-manifest markdown files in this folder are **not** published; they are only for repo readers or future inclusion once added to the manifest.
