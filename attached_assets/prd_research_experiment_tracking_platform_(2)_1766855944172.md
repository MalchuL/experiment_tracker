# PRD: Research Experiment Tracking Platform

## 1. Overview

### 1.1 Purpose

The goal of the project is to build a web service for managing, logging, and restoring ML/DS experiments, designed **specifically for researchers and research teams**. The platform is an alternative to W&B, TensorBoard, Aim, and ClearML, with a strong focus on:

- experiment reproducibility **even without git commits**;
- explicit experiment hierarchy (parent → child);
- structured *Features* representation (configurations, architectural and methodological decisions);
- flexible graph-based treatment of experiments as a knowledge structure;
- researcher-first workflows and hypothesis-driven analysis.

### 1.2 Target Users

- ML / DL Researchers
- Research Engineers
- Academic Labs
- Industry R&D Teams

### 1.3 Key Differentiators

- **Code diff logging** + AI-assisted experiment restoration
- Hierarchical **Feature Models** instead of flat configs
- Experiments represented as a **DAG**, not a flat list
- Built-in TensorBoard interception (monkey-patching)
- Retroactive editing of experiment relationships
- Experiment merging and reconciliation (AI-assisted if needed)

---

## 2. High-Level Architecture

### 2.X Technology Stack

#### Containerization & Deployment

- Docker (all components)

---

#### Backend

- **FastAPI** — core web framework
- **SQLAlchemy** — ORM
- **PostgreSQL** — primary relational database
- **Celery + Redis** — background jobs, async processing (artifact diffing, evidence recomputation)
- **MinIO (S3-compatible)** — artifact, code snapshot, and file storage
- **deepdiff** — structural diffing for Features and artifacts
- **FastAPI Users** — authentication, authorization, user management
- **fastapi-ddd** — domain-driven design foundation
  - explicit domain layer
  - repository pattern
  - service layer abstraction

---

#### Frontend

- **Next.js** (React + TypeScript)
- **shadcn/ui + Tailwind CSS** — UI system
- **React Flow** — experiment DAG & graph visualization
- **Recharts** — metrics, evidence, and trend visualization
- **react-diff-view** — code / feature / artifact diffs
- **TanStack Query** — server state & caching
- **Zustand** — client state management

---

#### SDK

- **httpx** — HTTP client
- **pydantic** — schemas & validation
- **typer** — CLI framework

---



### 2.1 Components

1. **Backend (Web Service)**

   - Microservices or modular monolith
   - REST + WebSocket / gRPC

2. **SDK**

   - Python SDK (MVP)
   - CLI
   - TensorBoard monkey-patch

3. **Frontend**

   - Web UI for projects, experiments, and analysis

---

## 3. Core Domain Model

### 3.0 Hypothesis

A **Hypothesis** is a first-class entity representing a formal research claim tested by experiments.

A hypothesis describes the *expected impact* of Feature or code changes on one or more key project metrics.

**Examples:**

- "AdamW with lr=1e-4 converges faster than SGD"
- "Increasing patch size improves accuracy under fixed compute"
- "Feature X improves F1 on dataset Y"

**Hypothesis Properties:**

- id
- project\_id
- title
- description
- author
- status: Proposed | Testing | Supported | Refuted | Inconclusive
- target\_metrics
- baseline: root | best | experiment\_id
- related\_features (optional)
- created\_at
- updated\_at

**Relationships:**

- Hypothesis ↔ Experiment: many-to-many
- One experiment may test multiple hypotheses
- One hypothesis is evaluated through multiple experiments

**Status Evaluation:**

- Computed automatically from linked experiments and target metrics
- Metric directionality respected (minimize / maximize)
- Manual override allowed

---

### 3.1 Project

A project corresponds to a single task or research direction.

Example: `ViT training on ImageNet`

**Properties:**

- id
- name
- description
- owner / team
- settings:
  - experiment naming regex
  - parent detection rules
  - feature diff policy
- created\_at

---

### 3.2 Experiment

An **Experiment** represents a single long-running execution.

**Properties:**

- id
- project\_id
- name (validated by project regex)
- status: Planned | Running | Complete | Failed
- parent\_experiment\_id (nullable)
- root\_experiment\_id
- features\_diff (JSON/YAML)
- git\_diff / code\_snapshot
- artifacts
- metrics
- logs
- progress (0–100%)
- timestamps (start / end)

Experiments form a **Directed Acyclic Graph (DAG)**.

---

### 3.3 Features

**Features** are a hierarchical description of experiment configuration.

**Format:** YAML or JSON

```yaml
Optimization:
  Optimizer:
    name: AdamW
    lr: 1e-4
  BatchSize: 16
  Loss: BCE
Model:
  name: ViT
```

**Key Properties:**

- Structure is **not fixed**
- Captures *all* relevant research decisions
- Stored as a separate file

**Backend Stores:**

- `features_diff` — diff relative to parent
- `features_full` — computed on demand (root + diffs)

---

### 3.4 Code Snapshot

Supported formats:

- git diff (uncommitted changes)
- patch file
- tarball snapshot
- git commit reference + diff

Additional:

- AI-based reconstruction (environment + diff → runnable state)

---

## 4. SDK

### 4.1 Core Responsibilities

- project registration
- experiment lifecycle management
- logging:
  - scalars
  - images
  - audio
  - video
  - text
  - tables
- Feature logging
- code logging
- **experiment file artifacts logging**
  - directory and file capture via patterns
  - incremental updates
  - binary and text support

---

### 4.2 SDK API (Example)

```python
from research_sdk import Experiment

exp = Experiment(
    project="vit_imagenet",
    name="12_from_8_lr_sweep",
    features="features.yaml"
)

exp.log_metric("loss", 0.42, step=10)
exp.log_image("attention", img)
exp.finish(status="complete")
```

---

### 4.3 TensorBoard Monkey-Patch

- intercepts `SummaryWriter`
- seamless legacy code migration
- PyTorch / TensorFlow compatible

---

### 4.4 CLI

```bash
rsdk restore --experiment 12
rsdk env build --experiment 12
rsdk rerun --experiment 12
```

---

## 5. Backend Logic

### 5.0 Evidence Model

The **Evidence Model** formalizes how experiments contribute to confirming or refuting hypotheses.

Its goal is to turn isolated runs into **accumulated research evidence**.

---

#### 5.0.1 Evidence Unit

An **Evidence Unit** is the atomic contribution of one experiment to one hypothesis.

Properties:

- hypothesis\_id
- experiment\_id
- metric\_name
- baseline\_value
- experiment\_value
- delta (signed)
- normalized\_delta
- direction (minimize / maximize)
- confidence\_score ∈ [0,1]
- timestamp

If a metric is missing → no Evidence Unit is created.

---

#### 5.0.2 Metric-Level Evidence

For each target metric:

1. Baseline selection:
   - parent
   - root
   - best experiment
2. Delta computation:
   - maximize: experiment − baseline
   - minimize: baseline − experiment
3. Robust normalization

Result: **signed evidence contribution**.

---

#### 5.0.3 Experiment-Level Evidence

```
E_experiment = Σ (w_metric × normalized_delta_metric)
```

Weighted by metric importance and confidence.

---

#### 5.0.4 Confidence Score

Confidence reflects experiment reliability:

- status (Complete > Failed)
- metric stability
- seed variation
- rerun consistency
- environment correctness

---

#### 5.0.5 Hypothesis-Level Aggregation

```
E_hypothesis = Σ (confidence_i × E_experiment_i)
```

---

#### 5.0.6 Hypothesis Status Decision

- E\_hypothesis > +T\_support → Supported
- E\_hypothesis < −T\_refute → Refuted
- otherwise → Testing / Inconclusive

Thresholds are project-configurable.

---

### 5.1 Experiment Startup Flow

1. SDK sends metadata
2. Backend:
   - parses experiment name
   - determines parent
   - loads parent features
   - computes diff
3. Adds node to DAG

---

### 5.2 Feature Diff Algorithm

- recursive structural comparison
- add / update / delete support
- minimal diff storage

---

### 5.3 Graph Recalculation

- parent change → recompute downstream
- full feature caching

---

### 5.4 Experiment File Artifacts

The platform captures **experiment files** from the local filesystem.

#### 5.4.1 File Capture Policy

Defined at project level:

- glob / regex patterns
- include / exclude rules
- size limits

```yaml
artifacts:
  include:
    - "checkpoints/*.pt"
    - "configs/**/*.yaml"
    - "results/*.json"
  exclude:
    - "**/*.tmp"
    - "cache/**"
```

---

#### 5.4.2 Artifact Storage Model

- full snapshot for root
- diff-based storage for children
- text diffs and binary hash diffs

---

#### 5.4.3 Artifact Versioning & Lineage

- content hash
- size
- mime type
- lineage tracked via experiment DAG

---

#### 5.4.4 SDK API (Artifacts)

```python
exp.log_artifacts(path="./outputs", policy="project-default")
```

---

## 6. Frontend

### 6.0 Project Metric Configuration

Projects define **key metrics** used for comparison.

Properties:

- name
- direction: minimize | maximize
- source: scalar | derived
- aggregation: last | best | average

Missing metrics → NaN.

---

### 6.1 Views

#### Hypothesis View

- hypothesis list
- status
- description
- linked experiments
- metric trends
- evidence summary

---

#### Project Metrics Overview

- experiment × metric table
- improvement / regression highlighting
- NaN indicators
- sorting and filtering

---

#### Experiment View

- parameters
- feature diff & full features
- code diff
- metrics
- artifacts
- hypothesis contributions
- file tree & side-by-side diffs

---

#### Graph View

- experiment DAG
- drag-and-drop parent reassignment
- metric improvement indicators

---

#### Kanban View

- Planned / Running / Complete / Failed

---

### 6.2 UX Features

#### Artifact Comparison

- side-by-side text diff
- inline highlighting
- experiment-to-experiment comparison
- binary fallback (hash / metadata)

---

#### Evidence Visualization

- hypothesis evidence dashboard
- waterfall charts
- metric contribution view
- timeline view
- DAG evidence overlay
- comparison & Pareto analysis

---

## 7. Auth & Collaboration

- Users
- Teams
- Roles: Admin / Researcher / Viewer
- Project-level permissions

---

## 8. Additional Features

### 8.0 Metric Analytics

- metric trends by DAG order
- baseline selection
- multi-metric Pareto analysis

---

### 8.1 AI Research Assistant

Capabilities:

- hypothesis generation
- experiment summarization
- cross-experiment reasoning
- next-experiment recommendations
- natural language queries

---

### 8.2 Reproducibility

- environment capture
- dataset versioning hooks

---

### 8.3 Integrations

- GitHub / GitLab
- Arxiv
- Slack / Telegram

---

### 8.4 Scalability

- S3-compatible storage
- pluggable databases

---

## 9. Non-Functional Requirements

- horizontal scalability
- fault tolerance
- GDPR compliance
- audit logs

---

## 9.5 MVP Cut (Scope Definition)

**Goal:** prove reproducible research + knowledge accumulation.

### Included

- Projects / Experiments / DAG / Kanban / List

- Users / Team

- Feature model (full + diff)

- Git diff capture

- Metrics difference

- Scalar metrics

- Basic UI + SDK + CLI

### Excluded

- video/audio artifacts
- large checkpoint streaming
- full AI recovery
- hypothesis auto-generation

---

### MVP Validation Criteria

- experiment restorable without git commit
- diffs are explainable
- files and metrics comparable

---

## 10. Pitch: Why This Wins

**One-liner:**

> A research-native experiment platform that turns runs into knowledge.

---

### Vision

From experiment tracking → **collective research intelligence**.

---

## 11. Success Metrics

- experiment restoration time
- reproducibility rate
- research team adoption

---

## 12. Open Questions

- AI recovery automation level
- diff storage format
- real-time logging SLA

---

**End of PRD**

