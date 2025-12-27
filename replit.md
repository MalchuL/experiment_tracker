# ResearchTrack - Experiment Tracking Platform

## Overview

ResearchTrack is a research-native experiment tracking platform for managing, logging, and restoring ML/DS experiments. It's designed specifically for researchers and research teams, offering:

- **Experiment Hierarchy (DAG)**: Experiments form parent-child relationships, enabling tracking of iterative research
- **Feature Model**: Hierarchical configuration tracking with diff computation
- **Hypothesis Management**: Track research claims and link them to experiments
- **Multiple Views**: Dashboard, List, Kanban, and DAG visualization
- **User Authentication**: JWT-based authentication with 7-day tokens
- **Team Collaboration**: Role-based access control (owner, admin, member, viewer)

## Architecture

### Dual Backend Architecture

The application uses a dual backend architecture:
1. **FastAPI (Python)**: Handles authentication, database models, and team management
2. **Express.js (Node.js)**: Serves frontend and proxies API requests

### Tech Stack

**Frontend:**
- React + TypeScript with Vite
- Wouter for routing
- TanStack Query for data fetching
- Shadcn/ui + Tailwind CSS for UI
- Lucide React for icons
- Auth context with JWT token management

**Backend (FastAPI):**
- FastAPI with FastAPI Users for authentication
- SQLAlchemy async with asyncpg driver
- PostgreSQL database
- JWT authentication (7-day tokens)
- Role-based access control

**Backend (Express):**
- Frontend static serving
- API proxy to FastAPI
- In-memory storage for experiments (legacy)

## Project Structure

```
backend/
├── main.py          # FastAPI app configuration
├── database.py      # SQLAlchemy async setup
├── models.py        # User, Team, TeamMember models
├── auth.py          # FastAPI Users configuration
├── routes.py        # Protected experiment/project routes
├── team_routes.py   # Team CRUD with role permissions
├── schemas.py       # Pydantic models
└── storage.py       # In-memory experiment storage
client/
├── src/
│   ├── components/
│   │   ├── ui/          # Shadcn components
│   │   ├── app-sidebar.tsx
│   │   └── ...
│   ├── pages/
│   │   ├── dashboard.tsx
│   │   ├── login.tsx
│   │   ├── register.tsx
│   │   ├── teams.tsx
│   │   └── ...
│   ├── lib/
│   │   ├── queryClient.ts  # With auth headers
│   │   ├── auth-context.tsx
│   │   └── utils.ts
│   └── App.tsx
server/
├── routes.ts        # Express proxy configuration
└── index.ts
shared/
└── schema.ts        # Domain models (Zod)
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

- **Dec 27, 2025**: Added user authentication and team management
  - Integrated FastAPI Users with JWT authentication (7-day tokens)
  - Created User, Team, and TeamMember database models
  - Implemented role-based access control (owner, admin, member, viewer)
  - Protected all API routes with authentication
  - Built login/register pages with auth context
  - Added teams management UI with member invitations

- **Dec 27, 2025**: Initial MVP implementation
  - Created domain models with DDD structure
  - Built full React frontend with all views
  - Implemented in-memory storage with seed data
  - Added dark mode support
  - Created Dashboard, Projects, Experiments, Hypotheses, Kanban, and DAG views
