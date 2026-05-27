# Metrics

Metrics are experiment-level comparison values. Use them for final, best, selected, or summary values that should appear in experiment tables, DAG nodes, sidebars, and reports.

Metrics are different from [scalars](/docs/domains/scalars): scalars are time series; metrics are current values for a metric key.

## Metric key

A metric row is identified by:

- `experimentId`
- `name`
- `label`

`label` is optional. Empty label strings are normalized to no label.

For a given experiment, `name`, and `label`, there is one metric row. Logging the same key again updates the previous value.

```python
tracker.add_metric("accuracy", 0.94, label="final")
tracker.add_metric("loss", 0.08, label="best")
```

If you need to keep the step where a metric was selected, log that as a separate metric:

```python
tracker.add_metric("accuracy", 0.94, label="final")
tracker.add_metric("accuracy_step", 12000, label="final")
```

## Labels

Labels let you separate values that should not be compared directly:

- dataset: `train`, `val`, `test`;
- split or benchmark: `imagenet`, `cifar10`;
- threshold: `iou-0.5`, `iou-0.75`;
- phase: `best`, `final`, `checkpoint-10`.

The UI displays labeled metrics as `name:label`. Avoid using `:` inside metric names or labels because experiments lists, DAG views, and sidebar displays use that separator for readable keys.

## Project tracked metrics

Project settings decide which metrics matter for comparison. A tracked metric stores:

- `name`;
- optional `label`;
- `direction`: `maximize` or `minimize`;
- `aggregation`: `best` or `last` in current aggregation behavior.

Direction tells the UI which value is better. For example, maximize `accuracy`, minimize `loss`.

Aggregation is used when project-level metric summaries need to choose a value:

| Aggregation | Meaning |
|-------------|---------|
| `last` | Use the most recently created matching metric row. |
| `best` | Use max or min according to direction. |
| `average` | Present in the model but not supported by aggregation code yet. |

:::note
Because the current metric key is unique per experiment/name/label, repeated SDK `add_metric` calls normally update the same row. Aggregation is most relevant to project summary code and future compatibility.
:::

## Display metrics

Display metrics are the visible subset of tracked metrics. They control columns and values shown in:

- experiment list;
- kanban and related experiment views;
- DAG view;
- experiment sidebar.

Use tracked metrics for "the project cares about this", then use display metrics for "show this metric by default".

## Project metric views

The metrics page can list metrics by experiment or project and can build a label-specific table. Label snapshots produce one row per experiment and one column per metric name for the selected label.

The CLI can dump those snapshots:

```bash
experiment-tracker metric dump --project-id <project-id> --label final --format table
experiment-tracker metric dump --project-id <project-id> --label final --format csv
```

## Related

- [Projects: tracked metrics](/docs/domains/projects#tracked-metrics)
- [Scalars](/docs/domains/scalars)
- [SDK: experiment logging](/docs/sdk/experiment-logging#scalars-and-metrics)
