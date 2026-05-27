# Scalars

Scalars are time-series values used to plot training progress: losses, accuracies, learning rates, scores, counters, and any numeric value that changes by step.

Scalars are not the same as project [metrics](/docs/domains/metrics). A scalar name can have many points over many steps. A metric name/label pair stores one current comparison value per experiment.

## What a scalar point contains

A scalar point belongs to one experiment and contains:

- scalar name;
- numeric value;
- step;
- timestamp;
- optional tags metadata.

The SDK high-level API is:

```python
tracker.add_scalar("train/loss", loss, global_step=step)
tracker.add_scalar("val/accuracy", accuracy, global_step=epoch)
```

## Supported values

Only finite numeric values should be logged. `NaN`, `Inf`, `-Inf`, and `null` are not supported for storage. The SDK checks this and logs a warning instead of sending the point.

:::warning
If you see missing scalar points, check training logs for SDK warnings about non-finite values.
:::

## Fetching and sampling

The scalars page restricts the number of points returned per plot. By default the web app requests up to `1000` points per plot through `NEXT_PUBLIC_SCALARS_MAX_POINTS_PER_PLOT`.

The scalars service paginates experiments first, then loads metric columns. For each experiment and scalar column it uses uniform sampling over non-null rows when `max_points` is set. `columns_per_query` controls how many scalar columns are queried concurrently; the default is `1`.

Live updates and manual refreshes merge newer points into cached plot data. The UI keeps the first and latest points where possible and thins the merged series across the step range.

## Dots on small series

Small series show larger dots so sparse data remains visible. The default dot threshold is `10` points and can be configured with `NEXT_PUBLIC_SCALARS_DOT_THRESHOLD`.

## Logged objects on the scalars page

At-step artifacts such as images and text are surfaced on the scalars page because they are indexed by experiment, name, type, and step in the scalars service. They are stored as object-storage blobs, while their lookup metadata lives next to scalar data.

## Cleanup and compaction

Experiment deletion removes scalar rows for that experiment. Project deletion drops project scalar tables. Project danger-zone cleanup can also remove the whole scalar storage slice for a project.

Scalar column compaction is available for project tables and drops all-null scalar columns while preserving base columns such as timestamp, experiment id, step, and tags.

## Related

- [Metrics](/docs/domains/metrics)
- [Artifacts: step artifacts](/docs/domains/artifacts#step-artifacts)
- [Metric display formatting](/docs/reference/metric-display-formatting)
