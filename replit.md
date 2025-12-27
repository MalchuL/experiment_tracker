# ResearchTrack - Experiment Tracking Platform

## Overview

ResearchTrack is a research-native experiment tracking platform for managing, logging, and restoring ML/DS experiments. It's designed specifically for researchers and research teams, offering:

- **Experiment Hierarchy (DAG)**: Experiments form parent-child relationships, enabling tracking of iterative research
- **Feature Model**: Hierarchical configuration tracking with diff computation
- **Hypothesis Management**: Track research claims and link them to experiments
- **Multiple Views**: Dashboard, List, Kanban, and DAG visualization

## Architecture

### Domain-Driven Design (DDD)

The backend follows DDD principles adapted from fastapi-ddd patterns:

- **Domain Layer**: Entities and value objects defined in `shared/schema.ts`
- **Application Layer**: Business logic in `server/storage.ts` (IStorage interface)
- **Infrastructure Layer**: In-memory repository implementation (MemStorage)
- **Presentation Layer**: REST API routes in `server/routes.ts`

### Tech Stack

**Frontend:**
- React + TypeScript with Vite
- Wouter for routing
- TanStack Query for data fetching
- Shadcn/ui + Tailwind CSS for UI
- Lucide React for icons

**Backend:**
- Express.js
- In-memory storage (MemStorage)
- Zod for validation

## Project Structure

```
client/
├── src/
│   ├── components/
│   │   ├── ui/          # Shadcn components
│   │   ├── app-sidebar.tsx
│   │   ├── empty-state.tsx
│   │   ├── loading-skeleton.tsx
│   │   ├── page-header.tsx
│   │   ├── stat-card.tsx
│   │   ├── status-badge.tsx
│   │   └── theme-toggle.tsx
│   ├── pages/
│   │   ├── dashboard.tsx
│   │   ├── projects.tsx
│   │   ├── project-detail.tsx
│   │   ├── experiments.tsx
│   │   ├── experiment-detail.tsx
│   │   ├── hypotheses.tsx
│   │   ├── hypothesis-detail.tsx
│   │   ├── kanban.tsx
│   │   └── dag-view.tsx
│   ├── lib/
│   │   ├── queryClient.ts
│   │   ├── theme-provider.tsx
│   │   └── utils.ts
│   └── App.tsx
server/
├── routes.ts        # API endpoints
├── storage.ts       # Domain/Repository layer
└── index.ts
shared/
└── schema.ts        # Domain models & validation
```

## Core Domain Models

### Project
- Research direction container
- Has many experiments and hypotheses
- Properties: id, name, description, owner, experimentCount, hypothesisCount

### Experiment
- Single execution/run
- Forms DAG with parent-child relationships
- Status: planned | running | complete | failed
- Properties: features, featuresDiff, gitDiff, progress, metrics

### Hypothesis
- Research claim to test
- Status: proposed | testing | supported | refuted | inconclusive
- Links to experiments via many-to-many relationship

### Metric
- Scalar values logged during experiments
- Direction: minimize | maximize

## API Routes

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | /api/dashboard/stats | Dashboard statistics |
| GET | /api/projects | List all projects |
| POST | /api/projects | Create project |
| GET | /api/projects/:id | Get project |
| PATCH | /api/projects/:id | Update project |
| DELETE | /api/projects/:id | Delete project |
| GET | /api/experiments | List all experiments |
| GET | /api/experiments/recent | Recent experiments |
| POST | /api/experiments | Create experiment |
| GET | /api/experiments/:id | Get experiment |
| PATCH | /api/experiments/:id | Update experiment |
| DELETE | /api/experiments/:id | Delete experiment |
| GET | /api/experiments/:id/metrics | Get experiment metrics |
| GET | /api/hypotheses | List all hypotheses |
| GET | /api/hypotheses/recent | Recent hypotheses |
| POST | /api/hypotheses | Create hypothesis |
| GET | /api/hypotheses/:id | Get hypothesis |
| PATCH | /api/hypotheses/:id | Update hypothesis |
| DELETE | /api/hypotheses/:id | Delete hypothesis |

## User Preferences

- Dark/light mode toggle (persisted in localStorage)
- Inter font for UI, JetBrains Mono for code/metrics

## Recent Changes

- **Dec 27, 2025**: Initial MVP implementation
  - Created domain models with DDD structure
  - Built full React frontend with all views
  - Implemented in-memory storage with seed data
  - Added dark mode support
  - Created Dashboard, Projects, Experiments, Hypotheses, Kanban, and DAG views
