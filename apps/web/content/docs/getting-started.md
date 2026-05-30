# Getting started

Welcome to **ResearchTrack**. This guide covers the basics of working in the web workspace.

![Diagram: sidebar with Projects, Documentation, Teams and the workspace header with Documentation and Projects](/docs/images/workspace-overview.svg)

## Projects

Open **Projects** from the sidebar or the top navigation to see every project you can access. Create a project from the workspace view, then open it to manage experiments, metrics, hypotheses, and more.

## Teams

Use **Teams** to collaborate. Team membership can grant access to projects; project settings show how access is inherited or overridden.

## Documentation

All product docs linked from **Documentation** in the header live in this section. Use the index at `/docs` or open a page from the menu.

:::tip
Authors can use **callouts** (warnings, tips, …) and **expandable sections** in Markdown—see [Callouts, details & formatting](/docs/reference/doc-features) for live examples.
:::

## Deeper guides

- [Workspace & navigation](/docs/getting-started/workspace) — sidebar, header, and docs layout.
- [Projects](/docs/getting-started/projects) — creating and working inside a project.
- [Domains](/docs/domains) — users, teams, projects, experiments, scalars, metrics, artifacts, hypotheses, and reports.
- [SDK](/docs/sdk) — install the Python SDK, configure the CLI, and log experiments from training scripts.
- [File descriptors & local services](/docs/getting-started/file-descriptors) — `Too many open files`, local `uvicorn --reload`, and where to look in the repo when scalars or the backend exhaust FDs.
- [Admin panel](/docs/reference/admin-panel) — `ADMIN_PANEL_KEY`, `/admin` user management, and `/admin/storage` for operators.
- [Callouts, details & formatting](/docs/reference/doc-features) — warning boxes and collapsible Markdown blocks.
- [Common documentation patterns](/docs/examples/common-patterns) — practical recipes for authors.
- [Adding documentation pages](/docs/contributing/adding-pages) — how authors and agents add new `/docs` pages.

## Images in documentation

Static files for docs live under **`apps/web/public/docs/`**. Anything there is served from the site root.

1. Add your file, for example `public/docs/images/my-screenshot.png`.
2. In markdown, use a **root-relative** URL (starts with `/`):

```markdown
![Describe the image for accessibility](/docs/images/my-screenshot.png)
```

Use PNG, JPEG, WebP, GIF, or SVG. Remote images are also allowed if you use a full `https://…` URL (same syntax). Keep alt text meaningful for screen readers.

## Next steps

- Read [Architecture overview](/docs/architecture-overview) for how services connect.
- Open a project and explore **Experiments** and **Metrics** for day-to-day tracking.
