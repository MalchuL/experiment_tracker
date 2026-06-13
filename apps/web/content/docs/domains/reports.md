# Reports

Reports are project-scoped documents for summarizing experiment results, decisions, and context. This area is under development and currently supports simple editable document blocks.

## Fields

| Field | Meaning |
|-------|---------|
| `id` | Stable report id. |
| `projectId` | Owning project. |
| `title` | Report title. |
| `content` | JSON document content. |
| `createdAt` / `updatedAt` | Timestamps. |

List responses return report summaries without the full document payload. Opening a report loads the full content.

## Editor blocks

The current editor supports simple blocks through a slash menu:

- text;
- headings 1-3;
- bullet list;
- ordered list;
- quote;
- code block;
- divider.

Inline formatting includes bold, italic, strike, inline code, and clear formatting.

## Intended use

Use reports to write human summaries around experiment data:

- why a run was created;
- which metrics matter;
- what changed from the parent experiment;
- what result should be used in a paper, dashboard, or handoff;
- links to datasets, docs, code, or external notes.

Reports complement metrics and scalars. Metrics answer "what was the value?", scalars answer "how did it evolve?", and reports answer "what did we learn?"

## Current limitations

Reports are still under development. The current implementation persists JSON document content and supports simple blocks; richer embedded experiment/metric widgets are not documented as supported behavior yet.

## Related

- [Experiments](/docs/domains/experiments)
- [Metrics](/docs/domains/metrics)
