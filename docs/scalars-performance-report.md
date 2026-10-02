# Scalar performance and refresh report

## Outcome

The project Scalars page now paginates plots (12 / 24 / 48), loads points only for cards within the viewport plus one card-height of overscan, and unmounts offscreen Plotly instances. Every plot still includes all selected experiments. Scalar names come from the existing lightweight project catalog; missing data for a selection is shown explicitly.

The existing deterministic step-coverage sampling is preserved. This is not randomized reservoir sampling. Merges still replace duplicate steps with incoming values, retain the first/latest points where capacity permits, preserve non-finite wire values, and cap each experiment/scalar series at the configured point limit.

## Findings in the previous implementation

- `useProjectScalars` eagerly exhausted experiment pages without scalar-name filters on the project Scalars page. Hidden and offscreen scalar columns were downloaded too.
- The data model prepared every metric, and the grid mounted every chart. Inactive tabs were force-mounted.
- Refresh watermarks lived in `previousByExperiment`, a component ref. Returning to a cached plot reset its baseline: the first poll established a new watermark without catching up the inactive interval.
- Watermarks advanced before point requests succeeded. Failed requests could permanently skip an interval on the next refresh.
- Refresh requests did not retain scalar-name filters, so adding pagination alone would still fetch all columns.
- Appending an incoming experiment to the first infinite-query page could duplicate an experiment already present in another page.

The initial targeted baseline passed 22 sampling/data-model/plot-series tests. Those tests did not exercise cache restoration or request failures.

## Implementation

### Loading and pagination

- The existing names endpoint supplies the catalog and refreshes on the live interval or manual refresh.
- URL/saved-view parameters `page` and `pageSize` preserve pagination. Filters and size changes reset the page; invalid pages clamp to the available range. Changing pages resets the scroll container to its top.
- Prefix grouping remains inside each page. A shared native `IntersectionObserver` observes fixed-size card placeholders against the actual scroll container. Offscreen, collapsed, and inactive-tab plots unsubscribe; fullscreen requests stay active independently.
- Artifact summaries retain their existing service and rendering. Their experiment selection now follows the regular query key rather than the removed scalar/artifact cache-injection effect. Artifact loading no longer blocks scalar rendering.
- Compare retains its existing filtered/bounded query hook and API behavior.

### Cache and refresh

- A React Query cache entry represents one scalar, project, experiment selection, and point limit. Data and successful per-experiment watermarks are stored together.
- A fresh request reads server watermarks before loading all experiment pages, bypassing the server point cache for that baseline. Incremental requests use the prior successful watermark inclusively.
- A failed or cancelled request commits neither data nor watermarks. React Query deduplicates concurrent requests for the same key. Cancellation is forwarded to Axios, and abandoned responses cannot overwrite a newer cache entry.
- Experiments are merged by ID once, instead of appending across infinite-query pages.
- Returning plots display cached data immediately and check all selected experiments, including completed experiments. Manual and timed refresh use the same transaction. Disabling auto-refresh stops the timer without disabling initial loading, return catch-up, or manual refresh.
- Unused entries retain the application's ten-minute cache lifetime. An evicted entry loads a full sampled baseline.

### Plot behavior

- Chart preparation and smoothing cover active scalar names only. React Query structurally shares unchanged data; unsmoothed plots no longer construct an unused smoothed series.
- Zoom domains remain above virtualized cards, preserving them through scrolling and plot-page changes. The existing SVG Plotly renderer, non-finite markers, hover, resize controls, synchronized domains, fullscreen, and point context menus remain.
- Creating a metric still uses the original scalar value, not the smoothed value. The dialog now includes an accessible description.
- No backend response schema or SDK API/version changes were required. Added dependencies are development-only: jsdom for lifecycle tests, Playwright and the already-used Vite version for the browser regression harness.

## Verification

- Frontend suite: 180 tests across 40 files (including nine jsdom lifecycle integration scenarios).
- TypeScript: `pnpm --dir apps/web run check-types` passed.
- New cache/virtualization/lifecycle/browser harness files pass targeted ESLint. Broader scalar lint still reports existing state-in-effect and ref-during-render patterns in artifact media, the refresh indicator, the metric dialog, and the extracted page controller; repository-wide lint is not claimed clean.
- Real headless Chrome with actual Plotly passed viewport loading, shared observer bounds, scrolling/unmounting, page return with new points, zoom restoration, and fullscreen checks. No browser page errors were recorded.
- The offline Python generator ran successfully, producing the workload below without Torch, NumPy, or another training framework. Its optional live SDK upload mode was not run against a deployment.
- Backend/ClickHouse integration was not run: backend code is unchanged and the browser harness intercepts API responses. These results verify frontend behavior, not backend throughput.

Regression coverage includes failed/incomplete experiment pagination, retained watermarks after failure, overlapping manual refresh, stale-response cancellation, full reload after eviction, empty experiment selection, collapsed groups, inactive tabs, paused polling, saved-view pagination, repeated dense sampled merges, and original-value metric creation.

## Component modularity follow-up

Scalar component props now group related values under `experiments`, `display`, `size`/`viewport`, `zoom`, `actions`/`interactions`, and selection-specific objects. Component prop interfaces and their nested groups contain at most nine fields, applying the requested 7 ± 2 upper bound without padding small interfaces. Existing prop types are reused for child panels and dialogs rather than duplicated.

- The route delegates to `ScalarsPage`; display state and dialog mutations have separate hooks, while `useScalarsPage` coordinates data and supplies typed view props.
- `ScalarsContentPanel` coordinates tabs. Plot pagination/grouping and pagination controls have separate components.
- `MetricChart` composes trace construction, layout configuration, interaction handling, and the hover tooltip from focused modules.
- Logged-object rendering separates grouping, cards, experiment rows, and media. Fullscreen scalar/artifact and experiment-edit dialogs are separate components.
- Settings panels forward nested props directly. The unused legacy `ScalarsControlsPanel` was removed. Compare and the browser fixture use the same grouped chart API.

The refactor preserves the sampling/cache implementation and original-value metric creation. After the split, all **180 tests in 40 files**, TypeScript checking, and the real-Plotly browser regression passed again. The browser retained the same payload sizes and chart counts: six initial charts, at most eight during scrolling, and restored latest step 1019 after navigating back. Zoom and fullscreen assertions also passed. No runtime dependency was added for this refactor.

## Measured browser workload

One reproducible local run: 8 experiments, 72 scalar names, 1,000 generated steps, every fifth scalar logged only every seventh step; 1,200 × 800 browser viewport and 560 × 300 plot sizing. The baseline harness reproduces the previous eager data preparation and all-chart mounting using the shared chart component; it is not a separately deployed old application build.

| Measurement | Eager baseline | Paginated / virtualized |
|---|---:|---:|
| Initial scalar point response bytes, uncompressed | 6,245,801 | 456,516 |
| Initial scalar point requests | 1 | 6 |
| Initially mounted Plotly charts | 72 | 6 |
| Chart preparation, final measured update | 25.2 ms | 7.4 ms |
| Load-to-settled sample, including harness startup and a 1.5 s settling wait | 5,837 ms | 2,471 ms |

Initial point bytes decreased **92.7%**, and mounted charts decreased **91.7%**. The tradeoff is multiple small per-scalar requests rather than one broad request. While scrolling, the virtualized view mounted at most **8** charts in this viewport. After advancing the synthetic server by 20 steps while on another plot page, returning preserved step 0 and reached step **1019** with maximum adjacent sampled-step gap ≤ 3. Zoom survived that page change, and fullscreen rendered successfully.

Timings are indicative single-machine samples, not production latency guarantees or FPS measurements. The deterministic payload sizes, chart counts, request filters, and restoration assertions are the stronger results. Larger viewports can mount more cards; the bound follows viewport plus overscan, not a hard-coded count of eight.

## Reproduce

From the repository root:

```bash
pnpm --dir apps/web install
pnpm --dir apps/web test
pnpm --dir apps/web run check-types
uv run --no-project python examples/scalars-performance/generate.py --dump /tmp/scalars-performance.json
pnpm --dir apps/web exec node tests/scalars-browser/run.mjs /tmp/scalars-performance.json
```

The browser runner uses `/usr/bin/google-chrome`; set `CHROME_PATH` to another compatible installed Chrome/Chromium executable. It starts a local Vite fixture server, intercepts scalar HTTP responses, prints measurements, asserts behavior, and closes both server and browser. No real project is modified.

To exercise a running deployment after configuring the SDK with its existing CLI:

```bash
uv run --project python/sdk examples/scalars-performance/generate.py --upload --project 'Scalar performance' --run navigation-check --experiments 8 --metrics 72 --steps 1000 --seconds 60
```

During logging, page through plots, collapse groups, navigate away and return, and create a metric from a point. Use a fresh `--run` name for independent runs; reusing a name follows the SDK's existing experiment resolution behavior.
