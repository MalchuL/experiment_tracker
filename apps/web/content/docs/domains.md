# Domains

Experiment Tracker is organized around a small set of product domains. Projects own experiments, experiments produce scalars, metrics, and artifacts, and teams/users decide who can see or change that data.

## Core model

| Relationship | Meaning |
|--------------|---------|
| Users -> Teams | Team membership grants shared access. |
| Users -> Projects | Direct project membership grants project-specific access. |
| Teams -> Projects | Team-owned projects inherit access from team roles. |
| Projects -> Experiments | Every experiment belongs to one project. |
| Experiments -> Scalars | Runs log time-series values for plots. |
| Experiments -> Metrics | Runs store comparison values. |
| Experiments -> Artifacts | Runs store at-step and final files. |
| Projects -> Artifacts | Projects can store shared CAS artifacts and snapshots. |
| Projects -> Hypotheses | Hypotheses describe project-scoped research claims. |
| Projects -> Reports | Reports summarize project results and decisions. |

## Pages

- [Users](/docs/domains/users) — accounts, profiles, password changes, superuser, and personal API tokens.
- [Admin panel](/docs/reference/admin-panel) — bootstrap operator UI (`ADMIN_PANEL_KEY`, `/admin`, storage admin).
- [Teams](/docs/domains/teams) — team ownership, roles, members, and team-owned projects.
- [Projects](/docs/domains/projects) — experiment containers, members, settings, tracked metrics, and display metrics.
- [Experiments](/docs/domains/experiments) — concrete runs, status, progress, colors, tags, parents, and feature trees.
- [Scalars](/docs/domains/scalars) — time-series values for plots and training progress.
- [Metrics](/docs/domains/metrics) — final or comparison values, labels, project metric settings, and UI display.
- [Artifacts](/docs/domains/artifacts) — at-step outputs, final experiment artifacts, and project CAS artifacts.
- [Hypotheses](/docs/domains/hypotheses) — project-scoped research claims and target metrics.
- [Reports](/docs/domains/reports) — project report documents for summarizing experiment results.

## What to use where

| You want to | Use |
|-------------|-----|
| Compare runs over time | [Scalars](/docs/domains/scalars) |
| Compare final run quality | [Metrics](/docs/domains/metrics) |
| Store checkpoints, configs, reports, or media | [Artifacts](/docs/domains/artifacts) |
| Explain what changed between related runs | [Experiments](/docs/domains/experiments#features-and-parent-diffs) |
| Control who can view or edit a project | [Projects](/docs/domains/projects#members) and [Teams](/docs/domains/teams) |
| Store reusable project metadata | [Project settings](/docs/domains/projects#settings) |

## Related

- [Architecture overview](/docs/architecture-overview)
- [SDK](/docs/sdk)
- [Projects getting started](/docs/getting-started/projects)
