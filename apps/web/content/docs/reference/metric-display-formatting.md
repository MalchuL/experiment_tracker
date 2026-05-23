# Metric display: precision & thresholds

One place controls how metric **values** are turned into **text** in the UI (tables, DAG, sidebar, selected metrics, and the logged-metric field when it is **blurred**). Adjust these when you want more detail, shorter cells, or calmer parent comparisons.

## Where to edit

| What | Path |
|------|------|
| **Defaults (change these)** | `apps/web/src/lib/constants/metric-display.ts` |
| Number → string wiring | `apps/web/src/lib/metrics/mathjs-metric-format.ts` (`formatValue`, `METRIC_FORMAT_OPTIONS`) |
| Shared formatter API | `apps/web/src/lib/metrics/metric-value-display.ts` |

Restart the Next.js dev server after editing constants so the UI picks up new values.

## What each setting changes

| Constant | What it affects on screen |
|----------|---------------------------|
| **`METRIC_DISPLAY_AUTO_FORMAT_PRECISION`** | **How many significant digits** you see. Higher = longer, more exact-looking text; lower = shorter, rounder. |
| **`METRIC_DISPLAY_AUTO_FORMAT_EXP_BOUND`** | **Plain decimals vs scientific** (`1e+7`, `1e-8`). Higher = keep `10000000` / long `0.000…` styles longer; lower = switch to `e` notation sooner for compact layout. |
| **`METRIC_DISPLAY_TIE_EPSILON`** | **Comparisons only** (parent vs child, deltas): tiny gaps show as **no change** (`+0` delta text and equality icon in delta UI, no better/worse hint). Does **not** change digit count. Higher = treat more differences as ties; lower = stricter, noisier. |

Focused logged-metric editing uses a **full decimal** string; that path ignores the exponent bound above. Save/skip rules for typed values are in `experiment-details-view.tsx`.

## Examples

Illustrative outputs for the same **numeric** inputs when only precision or exponent bound changes (defaults in the tables use `expBound = 6` or `precision = 7` as noted). Exact characters may shift slightly if the formatter library updates; the **pattern** stays the same.

### Precision (`METRIC_DISPLAY_AUTO_FORMAT_PRECISION`, `expBound = 6`)

| Input | `precision = 4` | `precision = 7` (default) | `precision = 10` |
|-------|-----------------|---------------------------|------------------|
| `0.012312312312312312` | `0.01231` | `0.01231231` | `0.01231231231` |

### Exponent band (`METRIC_DISPLAY_AUTO_FORMAT_EXP_BOUND`, `precision = 7`)

| Input | `bound = 4` | `bound = 6` (default) | `bound = 9` |
|-------|-------------|----------------------|-------------|
| `1e-6` | `1e-6` | `0.000001` | `0.000001` |
| `1e-8` | `1e-8` | `1e-8` | `0.00000001` |
| `100000` | `1e+5` | `100000` | `100000` |
| `1e7` | `1e+7` | `1e+7` | `10000000` |

:::tip
Want **`10000000`** instead of **`1e+7`**? **Raise** `METRIC_DISPLAY_AUTO_FORMAT_EXP_BOUND`. Prefer tighter cells? **Lower** it so **`e`** form appears earlier.
:::

### Tie epsilon (`METRIC_DISPLAY_TIE_EPSILON`, default `1e-10`)

Does not change how one number is printed. It changes **delta** and **vs parent** behavior (see `metric-value-display.ts`).

| Situation | With default `1e-10` |
|-----------|----------------------|
| Signed delta `5e-11` | Treated as tie → shows **`+0`** and equality styling (see `metric-value-display.test.ts`, `MetricDeltaVsParent`). |
| Signed delta `5e-9` | Shows a **non-zero** signed delta. |
| Child `1 + 5e-11`, parent `1`, maximize | No better/worse hint (`null`). |
| Child `1 + 5e-9`, parent `1`, maximize | Gap large enough → better/worse can show. |

## Tests and overrides

- Sample formatted strings: `apps/web/src/lib/metrics/mathjs-format.test.ts` and `metric-value-display.test.ts`.
- Per-component or test overrides: `new MetricValueDisplayFormatter({ autoFormatPrecision, autoFormatExpBound, tieEpsilon, ... })` (`MetricValueDisplayFormatOptions` in `metric-value-display.ts`).

:::note
This page is only **display**. Logged-metric **typing**, parsing, and when blur skips a save are handled in `experiment-details-view.tsx`.
:::

## Related

- [DAG view: metrics on nodes](/docs/reference/dag-view) — how many metric rows appear on each experiment card in the lineage graph (`DAG_NODE_MAX_DISPLAY_METRICS`).
