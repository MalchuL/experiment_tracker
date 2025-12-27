# Design Guidelines: Research Experiment Tracking Platform

## Design Approach

**Selected System:** Modern Data Application Pattern inspired by Linear, Vercel Dashboard, and GitHub's interface design language.

**Rationale:** This platform is a utility-focused, information-dense tool for researchers. The design prioritizes clarity, scanability, and efficient workflows while maintaining visual sophistication through precise typography, thoughtful spacing, and subtle depth.

---

## Core Design Principles

1. **Information Hierarchy First:** Data visibility trumps decoration
2. **Density with Breathing Room:** Pack information intelligently without overwhelming
3. **Consistent Patterns:** Researchers need predictability for deep work
4. **Sophisticated Minimalism:** Clean doesn't mean sparse

---

## Typography

**Font Stack:**
- **Primary:** Inter (Google Fonts) - body text, UI elements, data tables
- **Monospace:** JetBrains Mono - code diffs, experiment IDs, metrics

**Scale:**
- Hero/Page Titles: text-4xl (36px), font-bold
- Section Headers: text-2xl (24px), font-semibold
- Card/Component Titles: text-lg (18px), font-medium
- Body Text: text-base (16px), font-normal
- Captions/Meta: text-sm (14px), font-normal
- Code/Data: text-sm monospace

**Treatment:**
- Line height: leading-relaxed for paragraphs, leading-tight for headings
- Letter spacing: tracking-tight for titles, tracking-normal for body

---

## Layout System

**Spacing Primitives:** Use Tailwind units of **2, 4, 6, 8, 12, 16** (e.g., p-4, gap-6, mt-8, mb-12)

**Container Strategy:**
- Full-width dashboard: max-w-screen-2xl mx-auto
- Content areas: max-w-7xl mx-auto
- Reading content: max-w-4xl

**Grid Systems:**
- Experiment lists: Single column with expandable rows
- Metrics overview: CSS Grid with auto-fit columns (min 280px)
- DAG visualization: Full-width canvas with zoom/pan
- Comparison view: 2-column split for side-by-side analysis

---

## Component Library

### Navigation

**Top Bar:**
- Fixed position, full-width
- Project selector (dropdown) + breadcrumb navigation
- Search command palette (⌘K trigger)
- User menu + notifications (right-aligned)
- Height: h-16, border-b with subtle divider

**Sidebar:**
- Collapsible (expanded by default on desktop)
- Width: w-64 expanded, w-16 collapsed
- Navigation groups: Projects, Hypotheses, Experiments, Settings
- Active state: subtle background fill + border accent

### Data Display

**Experiment Cards:**
- Compact row format with expandable details
- Left: Status indicator (dot) + Name + ID (mono)
- Center: Key metrics (3-4 max) with delta indicators
- Right: Timestamp + Actions menu
- Padding: p-4, gap-3 between elements

**Metrics Table:**
- Fixed header on scroll
- Cell padding: px-4 py-3
- Zebra striping for rows
- Highlight improvements (green accent) and regressions (red accent)
- Missing data: grayed "—" placeholder

**DAG Visualization:**
- React Flow canvas with custom node components
- Node design: rounded-lg border with subtle shadow
- Edge styling: curved paths with directional arrows
- Zoom controls: bottom-right corner
- Minimap: bottom-left corner

**Diff Viewer:**
- Split-pane for code/feature diffs
- Line numbers in monospace
- Additions: green background (subtle)
- Deletions: red background (subtle)
- Unchanged context: muted text

### Forms & Inputs

**Input Fields:**
- Height: h-10 for text inputs, h-12 for textareas
- Padding: px-3 py-2
- Border: rounded-md with focus ring
- Labels: text-sm font-medium, mb-2

**Buttons:**
- Primary: Solid fill, rounded-md, px-4 py-2
- Secondary: Border outline, same dimensions
- Icon buttons: Square (w-10 h-10), centered icon
- Button groups: gap-2 spacing

**Select/Dropdown:**
- Match input height (h-10)
- Chevron indicator on right
- Dropdown menu: rounded-lg, shadow-lg, py-1

### Status & Feedback

**Status Badges:**
- Pill shape: rounded-full, px-3 py-1
- Sizes: text-xs or text-sm
- States: Running (blue), Complete (green), Failed (red), Planned (gray)

**Toast Notifications:**
- Bottom-right corner
- Width: w-96, rounded-lg
- Auto-dismiss after 4s
- Icon + message + dismiss button

**Progress Indicators:**
- Linear progress bars: h-2, rounded-full
- Circular loaders for async actions
- Skeleton screens for data loading (pulse animation)

### Overlays

**Modals:**
- Max width: max-w-2xl for forms, max-w-4xl for content
- Backdrop: semi-transparent dark overlay
- Padding: p-6
- Close button: top-right, icon-only

**Sidesheets:**
- Slide from right
- Width: w-1/2 or w-2/3 depending on content
- For experiment details, hypothesis editing

---

## Charts & Visualizations

**Recharts Configuration:**
- Line charts: Smooth curves, 2-3 metrics max per chart
- Bar charts: Comparison across experiments
- Scatter plots: Hyperparameter relationships
- Chart height: h-64 to h-80
- Grid: Subtle horizontal lines only
- Tooltips: rounded-lg shadow-md with full context

**Evidence Visualization:**
- Horizontal bar charts for hypothesis support
- Stacked metrics showing contribution
- Timeline view for experiment progression

---

## Animations

**Minimal Motion:**
- Page transitions: None (instant)
- Hover states: Subtle opacity/background changes (no transforms)
- Modal/drawer: Slide-in with 200ms duration
- Accordion expand: 150ms ease
- Loading states: Pulse/spin only

---

## Images

**Hero Image:** None - this is a data-focused application, not marketing.

**Supporting Images:**
- Placeholder images for empty states (illustration style)
- Experiment artifact thumbnails (if images logged)
- User avatars in team/owner displays

**Empty States:**
- Centered illustration + heading + description + CTA
- Illustrations: Simple, abstract representations of experiments/data

---

## Page-Specific Layouts

**Dashboard (Home):**
- Grid: Recent experiments (left 2/3) + Quick stats sidebar (right 1/3)
- Recent hypotheses widget
- Activity feed at bottom

**Hypothesis View:**
- Header: Title, description, status badge
- Tabs: Overview | Experiments | Evidence | Timeline
- Evidence chart prominent in Overview tab
- Linked experiments table

**Experiment Detail:**
- Sticky header: Name, status, actions
- Left sidebar: Metadata, parent link, timestamps
- Main content: Tabbed interface (Features | Metrics | Artifacts | Code | Logs)
- Feature diff: side-by-side or unified view toggle

**Project Metrics Overview:**
- Filterable table with column sorting
- Metric columns with directional indicators
- Row actions: Compare, View, Clone

**DAG Explorer:**
- Full-screen canvas
- Toolbar: Zoom controls, layout algorithm selector, filter
- Node inspector panel (slides in on node click)