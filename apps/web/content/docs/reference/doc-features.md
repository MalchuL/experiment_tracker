# Callouts, details & formatting

This page is a **live reference** for documentation blocks available in `content/docs/`. The blocks below are real examples (not screenshots).

## Callouts

Use **triple-colon** directives. Names are lowercase. You can use **bold**, lists, and [links](/docs/getting-started) inside the block.

### Info & note

:::info
**Info** is for neutral context: where a file lives, or what a term means. It is not urgent.
:::

:::note
**Note** highlights context readers might skip—background that helps interpretation without sounding alarmed.
:::

### Tips & warnings

:::tip
**Tip** suggests a workflow shortcut or convention your team recommends (safe improvements).
:::

:::caution
**Caution** marks reversible mistakes—wrong filters, confusing defaults—or anything that wastes time but does not destroy data by itself.
:::

:::warning
**Warning** is for actions that can cause wrong data, broken runs, or mixing experiments across projects if misunderstood.
:::

:::danger
**Danger** is for irreversible harm or security impact—credential leaks, destructive deletes, or compliance breaches.
:::

### Combining patterns

:::note
You can place **multiple paragraphs** in one callout.

- Bullet lists work.
- So does `inline code`.
:::

## Collapsible sections

Use `:::details` (or `:::collapse`) with a **`summary`** attribute. Body Markdown is rendered normally.

:::details{summary="Click to show YAML-style snippet"}

```yaml
experiment:
  name: baseline-run
  tags: ["demo", "docs"]
```

:::

:::details{summary="Expanded by default" open}

This block uses the **`open`** attribute so it starts uncollapsed—useful for short optional sections readers often want immediately.

:::

:::collapse{summary="`collapse` is an alias of `details`"}

Same behavior as `:::details`; pick whichever reads better in prose.

:::

## Quick syntax recap

| Block | Opening line |
|-------|----------------|
| Callout | `:::warning` … `:::` |
| Collapsible | `:::details{summary="Title"}` … `:::` |
| Start expanded | Add **`open`** next to summary: `:::details{summary="T" open}` |

## Related

- [DAG view: metrics on nodes](/docs/reference/dag-view) — cap on metric rows per experiment card in the project graph.
- [Common documentation patterns](/docs/examples/common-patterns) — recipes for onboarding and runbooks.
- [Adding documentation pages](/docs/contributing/adding-pages) — manifest + syntax guide for authors.
- [Extending the docs pipeline](/docs/contributing/extending-doc-pipeline) — how developers add new directive types, sanitization, and UI.
