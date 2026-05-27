# Hypotheses

Hypotheses are project-scoped research claims. This area is under development, but the backend and web UI already support basic CRUD and list flows.

## Fields

| Field | Meaning |
|-------|---------|
| `id` | Stable hypothesis id. |
| `projectId` | Owning project. |
| `title` | Short claim or question. |
| `description` | Longer explanation. |
| `author` | Author display value. |
| `status` | Current hypothesis state. |
| `targetMetrics` | Metric names the hypothesis cares about. |
| `baseline` | Baseline reference, defaulting to `root`. |
| `createdAt` / `updatedAt` | Timestamps. |

## Status

Supported status values are:

- `proposed`
- `testing`
- `supported`
- `refuted`
- `inconclusive`

## Intended use

Use hypotheses to capture what you believe should happen before running experiments:

- "Increasing batch size should improve throughput without reducing accuracy."
- "Adding augmentation should improve validation accuracy on the `val` label."
- "The new preprocessing pipeline should reduce `loss:final`."

Target metrics should match the project metric vocabulary where possible. That makes it easier to compare the hypothesis to experiments later.

## Current limitations

The feature is still under development. Today it is best treated as structured project notes with status and target metric fields. Deeper validation, automatic correctness checks, and richer links to experiments are expected to evolve around this domain.

## Related

- [Projects](/docs/domains/projects)
- [Metrics](/docs/domains/metrics)
- [Reports](/docs/domains/reports)
