# Projects

Projects are the main workspace unit for experiments. A project owns experiments, project settings, tracked/display metric configuration, members, reports, and project-level storage.

## Project fields

| Field | Meaning |
|-------|---------|
| `id` | Stable project id. |
| `name` | Project display name. |
| `description` | Optional project description. |
| `team` | Optional owning team. |
| `owner` | User who owns the project. |
| `experimentCount` | Number of experiments. |
| `metrics` | Tracked and displayed metric config. |
| `settings` | Typed project settings. |

Creating a project provisions scalar storage for that project. Deleting a project removes experiment data from object storage and scalars before deleting the Postgres project row.

## Experiments

Experiments are always project-scoped. Project pages use experiments for:

- list and kanban views;
- DAG view and parent/child comparisons;
- scalars plots;
- metrics tables;
- final artifact panels;
- storage and danger-zone cleanup.

## Members

Project members can come from three access sources:

| Source | Meaning |
|--------|---------|
| `direct` | The user has project-scoped permission rows or owns the project. |
| `team` | The user inherits access from the project owner's team. |
| `override` | The user belongs to the team and also has project-specific permission rows. |

Project maintainers can invite existing active users by email. Team-inherited users cannot be removed from a project directly; removing a project override makes them fall back to team access. Standalone projects guard against removing the last user with edit access.

## Tracked metrics

Tracked metrics define which metric dimensions matter for project comparison. Each tracked metric stores:

| Field | Meaning |
|-------|---------|
| `name` | Metric name, such as `loss` or `accuracy`. |
| `label` | Optional metric label, such as `final` or `val`. |
| `direction` | `maximize` or `minimize`; determines which value is better. |
| `aggregation` | `best` or `last` today; `average` exists in the model but is not supported by aggregation code yet. |

The direction is used when comparing a child experiment to its parent in the sidebar. It also helps readers understand whether a displayed value is good or bad.

## Display metrics

Display metrics are an ordered subset of tracked metrics. They control which metric columns are visible in experiment-heavy views:

- experiment list;
- kanban and related experiment views;
- DAG view;
- experiment sidebar.

If no display metrics are selected, no project metric columns are shown in those views. Display metrics can be reordered in project settings.

Metric labels render as `name:label`. Avoid `:` inside metric names or labels because UI keys and display labels use that separator.

## Settings

Project settings are typed name/value entries for project-level configuration. Supported setting types are:

- `int`
- `float`
- `string`
- `boolean`
- `json`

Use project settings for data that every experiment in the project may need to know or display, such as dataset URLs, documentation links, repo names, external service identifiers, config defaults, or pointers to secrets stored elsewhere.

:::warning
Project settings are project metadata. Do not store raw API keys or secrets there unless your deployment has explicitly made that acceptable. Prefer storing references to secret-manager keys.
:::

## Storage and cleanup

Project usage merges object-storage and scalars information:

- project CAS artifacts;
- snapshots;
- experiment buckets;
- scalar tables and bytes;
- total bytes.

Danger-zone cleanup can target project artifacts, snapshots, experiment buckets, or scalars without deleting the project row. Full project deletion performs broader cleanup and removes the project.

## CLI

```bash
experiment-tracker project list
experiment-tracker project get <project-id>
experiment-tracker project create --name "MNIST" --description "Classifier runs"
experiment-tracker project update <project-id> --name "MNIST v2"
experiment-tracker project delete <project-id> -y
```

## Related

- [Experiments](/docs/domains/experiments)
- [Metrics](/docs/domains/metrics)
- [Artifacts](/docs/domains/artifacts)
