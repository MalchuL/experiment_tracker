# Architecture overview

ResearchTrack is split into a browser UI, a primary API, and supporting services.

![Diagram: Web app to API, then to Scalars service and Object storage](/docs/images/architecture-linear.svg)

## Web application

The Next.js app provides the dashboard and proxies authenticated API calls. You configure it to talk to your backend base URL in development and production.

## Backend API

The main API owns users, teams, RBAC, projects, experiments, and orchestration. It calls other services over HTTP when loading scalars or handling file artifacts.

## Scalars service

Time-series metrics and artifact metadata used for charts and step-based artifacts are stored and queried through the scalars service (for example ClickHouse-backed APIs).

## Object storage

Binary artifacts (checkpoints, uploads at step, project-level blobs) go through object storage with content-addressed or tracked paths, depending on the upload flow.

## Further reading

See the repository `AGENTS.md` for endpoint-level flows and package layout for contributors.
