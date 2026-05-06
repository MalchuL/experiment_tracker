# Common documentation patterns

Recipes for structuring documentation pages in this app: when to use warnings, how to hide optional steps, and short patterns readers recognize quickly.

:::info
These patterns use the same directive syntax as [Callouts, details & formatting](/docs/reference/doc-features). Skim that page if you want to see every variant in one place.
:::

## Onboarding a new contributor

Start with context, then narrow to tasks.

:::note
Link out to the repo root **`AGENTS.md`** (or your team runbook) for machine-specific setup; keep this doc focused on the product.
:::

:::details{summary="First-day checklist (expand)"}

1. Join the team and get access to the tracker URL.
2. Create or join a **project** from the workspace.
3. Run through one experiment or metric view to confirm permissions.

:::

## Before you run training jobs

:::warning
Always confirm **project id** and **API base URL** in your environment before starting long runs. Wrong targets can log metrics to another team’s project.
:::

:::details{summary="Optional: SDK environment variables"}

Set endpoints and tokens exactly as shown in your team’s secret manager. Do not commit `.env` files to git.

:::

## After something goes wrong

:::danger
If credentials were exposed, **rotate tokens** and revoke old keys from **Profile → API tokens** before continuing.
:::

:::tip
For transient API errors, prefer **retry with backoff** in training scripts rather than hammering the same endpoint.
:::

## Short decision guide

| Situation | Pattern |
|-----------|---------|
| Could lose data or leak secrets | `:::warning` or `:::danger` |
| Nice shortcut or convention | `:::tip` |
| Long steps few readers need | `:::details{summary="..."}` |
| Extra definition or background | `:::note` or `:::info` |

## Related

- [Callouts, details & formatting](/docs/reference/doc-features) — visual reference for every block type.
- [Adding documentation pages](/docs/contributing/adding-pages) — how to add pages to the manifest.
