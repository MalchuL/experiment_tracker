# Frontend component reuse and extraction proposals

Reviewed: 2026-10-02. Repository baseline: `11c54ce`.

**Status: proposals for human validation. No frontend implementation changes were made.** Source similarity supports these suggestions, but does not establish that two screens should have identical product behavior. Reject or narrow any proposal whose assumptions do not match your intent.

## Scope and method

The review covers `apps/web`: all page entry points and their layout structure, shared components, domain components, hooks, stores, utilities, styles, and the three artifact Route Handlers. The source inventory contains 550 files, including 540 TypeScript/TSX files, 27 `page.tsx` entry points, eight layouts, and 37 test files. The domains are auth, projects, teams, experiments, hypothesis, metrics, scalars, logged objects, experiment artifacts, compare, reports, and API tokens.

I inventoried the whole source tree, traced imports and callers, read the main page/component flows, and compared repeated implementation blocks. Large components and duplicated interactions received closer review; framework primitives and editor support files were assessed primarily through their interfaces and consumers. This is a static reuse review, not an exhaustive correctness audit or a browser-tested UX assessment. No runtime equivalence, performance gain, or line-count saving has been measured.

Links below point to existing source files relative to this report. Symbol names identify the relevant blocks; line numbers are occasional snapshot locators and may drift. Proposed names are illustrative, not required APIs.

## Main recommendation

The frontend already has a useful shared layer. Extend and adopt it before building another one. The strongest new extractions are small interactions repeated in independently maintained screens: search pickers, pagination, parent selection, confirmation dialogs, labeled sliders, and sidebar resizing.

Reuse should standardize an interaction, not merely move JSX into another file. Fetching, permissions, cache invalidation, persistence scope, and domain-specific mutations should generally remain with the owning domain/page.

| Proposal | Priority | Confidence | Relative effort | Main benefit |
| --- | --- | --- | --- | --- |
| E1. Share metric/scalar search picker | First | High | Small | One implementation of filtering, dismissal, selection, and keyboard behavior |
| E2. Reuse experiment picker for parent selection | First | High for duplication; medium for fit | Medium | Same parent-search and clear behavior in sidebar/details/create |
| E3. Extract member invitation and identity controls | First | High | Medium | Team/project screens share controls while preserving permission rules |
| E4. Share async confirmation and storage cleanup presentation | First | High | Medium | Consistent pending/error/confirmation behavior |
| E5. Share admin offset pagination | First | High | Small | Five tables use the same navigation behavior |
| E6. Extract labeled plot slider | First | High | Small | Remove almost identical controls from two comparison plots |
| E7. Share sidebar resize interaction | Next | High | Medium | One implementation of bounds, direction, and listener cleanup |
| E8. Share workspace/project shell chrome | Next | High for overlap | Medium | Consistent header, theme/user controls, and sidebar container |
| E9. Share clipboard interaction | Next | High | Small | Consistent feedback and copy failures across screens |
| E10. Extract auth presentation and password input | Next | High | Small–medium | Same authentication form presentation and reveal interaction |
| E11. Share diff expansion/navigation pieces | Next | High for duplication | Medium | Unified and side-by-side diff modes behave consistently |
| E12. Share sortable metric-order list | Next | High for overlap | Medium | Consistent drag controls in settings and metrics |
| E13. Extract experiment summary/status/progress pieces | Next | High for local duplication | Small–medium | Consistent experiment presentation without one universal card |
| E14. Separate large page-local panels | Optional | High for separability; low for cross-page demand | Small–medium | Clear component boundaries; future reuse remains unproven |
| E15. Reuse preview pieces across artifact/snapshot views | Optional | Medium–low | Medium | More consistent file inspection if that is desired |

“First” means strongest candidates for review, not an instruction to implement all of them. Effort is a qualitative comparison, not a time estimate.

## Existing components to reuse or extend

### Application-wide building blocks

| Existing component | Current use / behavior | Where it can be reused or extended | Boundary to preserve |
| --- | --- | --- | --- |
| [PageHeader](../apps/web/src/components/shared/page-header.tsx) | Titles, descriptions, optional actions across most pages | Replace hand-written headings in admin and storage management. Add a narrowly justified slot only if a real consumer cannot use `actions` | Workspace header actions are registered separately through `useWorkspaceHeaderActions`; decide deliberately which header owns an action |
| [EmptyState](../apps/web/src/components/shared/empty-state.tsx) | Icon, title, description, optional action; used by lists and scalar content | Replace repeated “No Project Selected” blocks in experiments, kanban, hypotheses, and settings; allow compact presentation only if needed | Missing selection, initial loading, load failure, and an empty successful result are different states |
| [Loading skeletons](../apps/web/src/components/shared/loading-skeleton.tsx) | `DashboardSkeleton`, `ListSkeleton`, `DetailSkeleton` | Keep these as the default for matching page shapes; use existing `Skeleton` directly for table-specific placeholders | A list of cards is not a faithful placeholder for every chart/table/editor |
| [StatCard](../apps/web/src/components/shared/stat-card.tsx) | Dashboard count/value, icon, description, optional trend | Storage usage/count summaries where this presentation fits; modest layout extension if needed | Do not force dense cleanup tiles into a large dashboard card |
| [StatusBadge](../apps/web/src/components/shared/status-badge.tsx) | Experiment and hypothesis status labels/colors | Continue using it in entity lists, summaries, and details | User active/verified state and API-token revoked state are different vocabularies |
| [EntityIdDisplay](../apps/web/src/components/shared/entity-id-display.tsx) | Copyable identifier with success/failure feedback | Profile user ID and team ID; admin IDs if copy-on-click is wanted | Do not turn every identifier into an interactive element without a UX decision |
| [CompareLabeledSwitch](../apps/web/src/domain/compare/components/compare-labeled-switch.tsx) | Associated label, switch, optional tooltip; already used outside compare | Other table wrap/pin controls and scalar name wrapping. Moving/renaming to `LabeledSwitch` is reasonable when touching it | Preserve IDs, disabled state, tooltips, and labels; a rename alone does not improve behavior |
| [RightSidebarShell](../apps/web/src/components/shared/right-sidebar-shell.tsx) | Header/actions/close, push or overlay placement, resize-handle callback | More experiment/settings side panels | It renders a handle but does not own resize state. Left rails and collapsible file trees have different placement contracts |
| [WorkspaceShell](../apps/web/src/components/shared/workspace-shell.tsx) | Shared workspace chrome for projects, teams, docs, profile, about, and admin | Extract its overlapping chrome with project layout, as E8 describes | Keep workspace scope controls and project context/navigation separate |

### Tables, experiment selection, and experiment inspection

| Existing component or hook | Current use / behavior | Reuse opportunity | Boundary to preserve |
| --- | --- | --- | --- |
| [ProjectDataTableFrame](../apps/web/src/components/shared/project-data-table-frame.tsx) | Shared scroll viewport, toolbar/footer, pinned-column context; used by experiments, metrics, and compare tables | Use as the table shell when the same full-height scrolling/pinning behavior is required | It does not implement sticky cells, sorting, resizing, or data fetching; consumers still do that |
| [ExperimentDataCompareTable](../apps/web/src/domain/compare/components/experiment-data-compare-table.tsx) | Metrics/hparams comparison; baseline/previous reference, diff classification, wrap/pin controls, persisted layout | Other experiment-by-field comparisons that truly use that reference model | Details overview compares metrics to each experiment's actual parent. That is not the same as selected baseline/previous |
| [Ordered selection hook](../apps/web/src/domain/experiments/hooks/use-ordered-experiment-selection.ts), [ExperimentCompareBar](../apps/web/src/domain/experiments/components/experiment-compare-bar.tsx), [selection badge](../apps/web/src/domain/experiments/components/experiment-selection-order-badge.tsx) | Already shared by experiments table, metrics table, and DAG | Add selection elsewhere by reusing these pieces | Inspecting one experiment, selecting ordered comparisons, and choosing visible scalar series are separate states |
| [CompareExperimentPicker](../apps/web/src/domain/compare/components/compare-experiment-picker.tsx) | Searchable experiment dropdown, selected value, loading, disabled IDs, optional “none” entry | Parent selection and other experiment lookup controls, with E2's extensions | The current trigger is disabled by loading, not an independent saving/disabled prop; missing selected records also need handling |
| [ExperimentTruncatedText](../apps/web/src/domain/experiments/components/experiment-truncated-text.tsx) | Table/card truncation and tooltip behavior; already shared by table and kanban | Experiment names/descriptions in new matching summaries | DAG names, chart hover labels, and editable names may need different wrapping/interaction |
| [ExperimentSidebar](../apps/web/src/components/shared/experiment-sidebar.tsx) | Shared inspector used by experiments, kanban, DAG, and project metrics | Continue using it for inspection; reuse internal controls rather than making a second inspector | It owns polling, persisted tabs, drafts, and heavy-tab loading; it is not a generic container |
| [ExperimentEditForm](../apps/web/src/components/shared/experiment-edit-form.tsx) | Core edits reused by sidebar, details, and scalar edit dialog; supports parent drafts and `afterDescription` | Other experiment edit surfaces | Creation has different defaults, fields, and lifecycle; E2 should share the parent control, not force creation into this form |
| [ExperimentSidebarLoggedMetrics](../apps/web/src/components/shared/experiment-sidebar-logged-metrics.tsx) and [LoggedMetricAddDialog](../apps/web/src/components/shared/logged-metric-add-dialog.tsx) | Logged metrics already shared by sidebar and details; add dialog is extracted | A logged-metric editor on another page should reuse the panel or its existing dialog | Naming is sidebar-specific, but functionality is already reused; a new “details metrics editor” would duplicate it |
| [MetricNameValueDiffRow](../apps/web/src/components/shared/metric-name-value-diff-row.tsx) | Shared value/delta rendering in sidebar, logged metrics, DAG, details, and compare metrics | Additional parent/reference metric displays | Reference value and direction must come from the caller; formatting reuse does not imply the same comparison semantics |
| [ExperimentHparamsPanel](../apps/web/src/components/shared/experiment-hparams-panel.tsx), [ExperimentHparamsTree](../apps/web/src/components/shared/experiment-hparams-tree.tsx), [ExperimentFeaturesPanel](../apps/web/src/components/shared/experiment-features-panel.tsx) | Panels are already shared by sidebar and details | Other experiment inspection surfaces | Parent diff behavior, lazy queries, editing, and experiment selection should remain explicit |
| [FeatureBulletEditor](../apps/web/src/components/shared/feature-bullet-editor.tsx), [feature help](../apps/web/src/components/shared/feature-editor-help.tsx), [ExperimentTagsEditor](../apps/web/src/domain/experiments/components/experiment-tags-editor.tsx) | Existing feature/tag editing widgets | Reuse in additional experiment forms | Feature trees and ordinary rich-text report documents are different data models |

### Charts, files, and content

| Existing component | Current use / behavior | Reuse opportunity | Boundary to preserve |
| --- | --- | --- | --- |
| [MetricChart](../apps/web/src/domain/scalars/components/metric-chart.tsx) | Scalar series rendering, hover modes, smoothing, zoom/domain callbacks; used on scalar page/dialogs and scalar compare | Any additional scalar-curve view with compatible data | Despite its name, it is a scalar/time-series chart. Aggregate metric comparison uses Recharts and a different model |
| [ScalarCardResizeHandle](../apps/web/src/domain/scalars/components/charts/scalar-card-resize-handle.tsx) | Already reused by scalar chart cards and both comparison plot cards | More cards needing these size bounds | Fixed bounds and two-axis gesture are part of its current contract; comparison consumers only use the resulting height |
| [MemoizedPlot](../apps/web/src/domain/scalars/components/plotly/stable-plot.tsx) and [Plotly theme helpers](../apps/web/src/domain/scalars/components/plotly/plotly-theme.ts) | Already shared by scalar charts and logged Plotly artifacts | Additional Plotly views | Preserve stable references, update freezing, and relayout callbacks; do not introduce a second wrapper |
| [ScalarExperimentList](../apps/web/src/domain/scalars/components/view-settings/scalar-experiment-list.tsx), [ScalarVisibilityList](../apps/web/src/domain/scalars/components/view-settings/scalar-visibility-list.tsx), [ScalarSavedViewsSection](../apps/web/src/domain/scalars/components/view-settings/scalar-saved-views-section.tsx) | Existing scalar view-control pieces | Reuse matching scalar visibility/saved-view UI | Checkbox visibility, solo selection, and ordered compare selection must remain distinct |
| [CollapsibleSidebar](../apps/web/src/domain/compare/snapshots/components/collapsible-sidebar.tsx) | Left/right file-tree sidebar with header action and internal collapsed state | Other file-browsing panels | Plot settings rails require controlled collapse and different widths/scrolling; extension needs proof of fit |
| [FileDropzone](../apps/web/src/components/shared/file-upload/dropzone.tsx) and [useFileDropzone](../apps/web/src/components/shared/file-upload/use-file-dropzone.ts) | Actual named-artifact upload already uses these shared pieces | Other real file-input surfaces | Selection UI is reusable; endpoint, metadata, replacement/CAS behavior, validation, and upload mutation remain domain-specific |
| [StructuredArtifactPreview](../apps/web/src/components/shared/structured-artifact-preview/structured-artifact-preview.tsx) | Named artifact previews: image, JSON/YAML/TOML tree, Markdown/text, and unsupported-result states | Other compatible previews; E15 evaluates snapshot integration | Currently coupled to `NamedArtifactPreview`, with preview-status assumptions and parsing behavior |
| [ArtifactMedia](../apps/web/src/domain/scalars/components/artifacts/artifact-media.tsx), [ImagePreviewDialog](../apps/web/src/domain/scalars/components/artifacts/image-preview-dialog.tsx) | At-step media; image expansion includes interpolation selection | Matching image/audio/video/Plotly surfaces | Named artifacts use a different preview transport and fullscreen UI; sharing an image renderer does not unify transport |
| [FileViewer](../apps/web/src/domain/compare/snapshots/components/file-viewer.tsx), [SyntaxHighlightedCode](../apps/web/src/domain/compare/snapshots/components/syntax-highlighted-code.tsx), [InlineDiffText](../apps/web/src/domain/compare/snapshots/components/inline-diff-text.tsx) | Snapshot file rendering and syntax/intraline highlighting | Plain source-code artifact display where desired | Keep binary/size/UTF-8 restrictions at the loading boundary |
| [MarkdownPreview](../apps/web/src/components/shared/markdown-preview.tsx) | Sanitized lightweight Markdown for uploaded content | Additional user-content Markdown surfaces | [DocsMarkdown](../apps/web/src/components/docs/docs-markdown.tsx) additionally supports directives, raw HTML processing, headings/TOC, and doc links; do not substitute it blindly |
| [SimpleReportEditor](../apps/web/src/domain/reports/components/simple-report-editor.tsx) | JSON rich-text editor composed from existing Tiptap support widgets | A second compatible report-document editor | Report loading/saving, draft initialization, and editor recreation remain outside the widget |

## Extraction proposals

### E1. One search picker for metrics and scalars

**Evidence:** [MetricsCompareMetricPicker](../apps/web/src/domain/compare/metrics/components/metrics-compare-metric-picker.tsx) and [ScalarsCompareScalarPicker](../apps/web/src/domain/compare/scalars/components/scalars-compare-scalar-picker.tsx). Both keep query/open state, install the same outside-pointer/Escape listeners, display filtered options, and reset/close after selection.

**Proposal:** one small picker under `domain/compare/components/`, with thin metric/scalar wrappers if their option types need them. The shared control needs stable option identity, display text, selected callback, placeholder/empty messages, and exclusion support. The installed `Command`/`Popover` primitives are worth checking before retaining custom dropdown event handling; that choice still requires keyboard and focus validation.

**Keep distinct:** metric identity includes name plus nullable label; scalar identity is the scalar name. Keep `uniqueDimensionsToOptions` and metric-specific normalization with metrics.

**Validate:** exclusion of already-added metrics, duplicate names with different labels, no available options versus no matches, pointer selection, Escape/outside dismissal, keyboard navigation, and focus after selection. High-confidence duplication; accessibility equivalence is not established by this review.

### E2. Standardize experiment parent selection

**Evidence:** parent picker state and JSX in [ExperimentSidebar](../apps/web/src/components/shared/experiment-sidebar.tsx), `ExperimentDetailsMetadataCard` in [ExperimentDetailsView](../apps/web/src/domain/experiments/components/experiment-details-view.tsx), and the simpler parent select in [CreateExperimentDialog](../apps/web/src/domain/experiments/components/create-experiment-dialog.tsx). Sidebar and details duplicate filtering, focus, draft selection, clear action, and `formatExperimentParentOption`.

**Proposal:** first extend/reuse `CompareExperimentPicker`; expose a narrow `ExperimentParentPicker` wrapper only for parent-specific behavior. Likely additions are explicit disabled state, custom option/selected labels, a selected-record fallback, and a clear/none interaction. Keep draft parent state in the form/caller.

**Keep distinct:** sidebar/details commit the draft with Save. Creation's `selectParentExperiment` also copies features from the chosen parent; the shared picker must call that existing handler. Parent validity and DAG cycle rules belong to domain validation, not a presentation component.

**Validate:** exclude the current experiment, unavailable/loading parent fallback, saving-disabled controls, clear parent, search reset/focus, draft-only edits, and feature inheritance during creation. Do not assume the comparison picker is a drop-in replacement today.

### E3. Member invitation and member identity controls

**Evidence:** [team detail page](../apps/web/src/app/(core)/(workspace)/teams/[teamId]/page.tsx) and [ProjectMembersPanel](../apps/web/src/domain/projects/components/settings/project-members-panel.tsx). Both implement email lookup, resolved-user state, role options, invite controls, initials/avatar/name/email cells, and role changes.

**Proposal:** extract `MemberInviteForm`, `MemberIdentity`, and a role-select control only if it remains substantial after reusing `Select`. Share the role labels (`admin` → Maintainer, `member` → Developer, `viewer` → Guest). Start with these fragments rather than a configurable universal members table.

**Keep distinct:** team owner/admin restrictions; project owner and server-provided `canEdit`/`canRemove`; project source badges (`team`, `override`, `direct`); and removal semantics. Team invitation sends a resolved user ID; project invitation sends an email. Mutations and cache keys remain in their existing domain hooks.

**Validate:** the resolved lookup still matches the current email after edits or delayed responses, pending/error states, owner restrictions, per-project role overrides, and restoring team inheritance when an override is removed. Common controls must not decide access policy.

### E4. Async confirmation dialogs and storage cleanup tiles

**Evidence:** [ProjectDangerZone](../apps/web/src/domain/projects/components/settings/project-danger-zone.tsx), [ExperimentDangerZoneCard](../apps/web/src/domain/experiments/components/experiment-danger-zone-card.tsx), [TeamDangerZone](../apps/web/src/domain/teams/components/team-danger-zone.tsx), [FinalArtifactCard](../apps/web/src/domain/experiment-artifacts/components/final-artifact-card.tsx), [report list](../apps/web/src/app/(core)/projects/[projectId]/reports/page.tsx), and [API tokens](../apps/web/src/app/(core)/profile/api-tokens/page.tsx). Repeated dialogs combine title/description, Cancel, destructive submit, and pending text. Project/experiment danger zones also repeat usage tiles and category confirmation.

**Proposal:** a controlled `ConfirmActionDialog` composed from the existing `AlertDialog`; callers supply open state, description, labels, pending state, and confirmation handler. Separately extract a small `StorageUsageGrid` for byte counts and “Clean…” callbacks in the two danger zones. Share the collapsible danger-card header only if enough duplication remains.

**Keep distinct:** cleanup categories, errors from satellite services, delete/transfer/revoke operations, success-only closing, navigation, and invalidation. Team deletion is not the same cascade as project or experiment deletion. Do not bury mutation execution in the dialog.

**Validate:** one action per click, no accidental close while pending, errors leave a usable dialog, correct target/category descriptions, and warnings remain visible. Admin pages use native `window.confirm`/`prompt`; changing those to the component is a separate UX migration, not required for extraction.

### E5. Admin pagination controls

**Evidence:** users, projects, and teams in [admin page](../apps/web/src/app/admin/page.tsx), plus buckets and scalar tables in [storage management](../apps/web/src/app/admin/storage/page.tsx). All five repeat range summaries and Previous/Next buttons; all also have page-size controls.

**Proposal:** controlled `OffsetPagination` with offset, page size, loaded count, total, pending/disabled state, and offset-change callback. A shared page-size select can be part of the same small admin-specific module. Reuse existing `Button` and native/select primitives; no table abstraction is needed.

**Keep distinct:** admin options are 10/20/50, storage options are 25/50/100. Search/debounce, filters, response shapes, table columns, and loaders remain local. Reset offset on the caller's relevant filter/size changes.

**Validate:** empty result, final partial page, changing size/filter, deleting the last row on a page, and Next availability. A nonzero total with an empty current page must not produce a misleading range. Do not apply this UI to auto/infinite-scrolling experiment lists.

### E6. Shared labeled slider and plot placeholder

**Evidence:** `PlotSliderField` in [metrics compare plot](../apps/web/src/domain/compare/metrics/components/metrics-compare-plot-chart.tsx) and [scalars compare plot](../apps/web/src/domain/compare/scalars/components/scalars-compare-plot-card.tsx) is almost identical; `unit` versus `valueSuffix` is the main interface difference. `SliderRow` in [ScalarDisplayControls](../apps/web/src/domain/scalars/components/view-settings/scalar-display-controls.tsx) is another close match. The compare plot files also both define `PlotPlaceholder`.

**Proposal:** `LabeledSlider` built from existing `Label`/`Slider`, with value, bounds, step, suffix or formatted value, change callback, and optional commit callback. Extract the simple height-aware `PlotPlaceholder` into compare components if sharing it still removes worthwhile duplication.

**Keep distinct:** scalar smoothing has separate live-change and commit handling; preserve it. Plot settings, queries, series builders, y-bound parsing, step bounds, and sampling are not generic slider concerns.

**Validate:** IDs/labels, min/max/step, value text, empty value-array protection, and change-versus-commit timing. `ScalarCardResizeHandle` is already shared by all three card families; no second resize component is needed.

### E7. Shared sidebar width resizing

**Evidence:** resize listeners in [ExperimentSidebar](../apps/web/src/components/shared/experiment-sidebar.tsx), [ScalarExperimentsSidebar](../apps/web/src/domain/scalars/components/view-settings/scalar-experiments-sidebar.tsx), and [ScalarViewSettingsSidebar](../apps/web/src/domain/scalars/components/view-settings/scalar-view-settings-sidebar.tsx). All record pointer/start width, clamp on move, and remove listeners on release.

**Proposal:** a small `useSidebarResize` hook for those three consumers. Pass direction and bounds explicitly; retain the current width state placement or return it from the hook. Existing `RightSidebarShell` remains the renderer for the right-hand panels.

**Keep distinct:** left sidebar width grows with rightward movement; right sidebar width grows with leftward movement. Experiment inspector uses an additional viewport-dependent maximum. Starting widths and min/max values differ.

**Validate:** dragging both sides, clamping, viewport limits, release outside the handle, pointer cancellation/unmount cleanup, and resizing while changing inspected records. Do not include DAG node resize: React Flow coordinates/zoom and node layout persistence are a different interaction.

### E8. Shared shell chrome

**Evidence:** [WorkspaceShell](../apps/web/src/components/shared/workspace-shell.tsx) and [project layout](../apps/web/src/app/(core)/projects/[projectId]/layout.tsx) repeat `TooltipProvider`, sidebar size variables, `SidebarProvider`/`SidebarInset`, a sticky header, theme/user controls, docs navigation, and main-content framing.

**Proposal:** extract a small shell/header composition with sidebar, header-leading content, header actions, and content/scroll classes as slots. Alternatively, share just the header first if moving the whole shell creates too many options.

**Keep distinct:** `ProjectProvider`, project sidebar/routes, workspace scope circles/header-action registration, and page-dependent full-height versus document-scroll layouts. Keep route decisions close to project layout; do not make a universal route-to-layout registry.

**Validate:** project navigation, workspace header actions, sidebar collapse, theme/user menu, docs navigation, narrow viewport, and all full-height tables/charts/DAG views. Nested `overflow` or missing `min-h-0` can break behavior despite matching markup.

### E9. Clipboard feedback

**Evidence:** [EntityIdDisplay](../apps/web/src/components/shared/entity-id-display.tsx), [API-token page](../apps/web/src/app/(core)/profile/api-tokens/page.tsx), custom setting value copying in [project settings](../apps/web/src/app/(core)/projects/[projectId]/settings/page.tsx), and copying in [ExperimentHparamsTree](../apps/web/src/components/shared/experiment-hparams-tree.tsx).

**Proposal:** reuse `EntityIdDisplay` for identifiers. Extract a small clipboard helper/hook for feedback and optional copied-state timing; use `CopyButton` only when several consumers need the same button presentation. Leave richer tree menu items and copyable setting surfaces in place.

**Keep distinct:** copied text construction (raw token, SDK config, setting value, JSON path/subtree), success messages, and display presentation. Do not persist token/config text or log it through shared copy handling.

**Validate:** clipboard rejection, repeated clicks/timer cleanup, labels, and exact copied payload. A generic “copy anything” card is unnecessary.

### E10. Auth card and password reveal input

**Evidence:** [login](../apps/web/src/app/(auth)/login/page.tsx) and [register](../apps/web/src/app/(auth)/register/page.tsx) repeat page backdrop, centered branding, card headers, account-switch footer, and reveal-password controls. [Profile](../apps/web/src/app/(core)/profile/page.tsx) has three plain password fields.

**Proposal:** an auth-local `AuthCard`/page presentation plus `PasswordInput` forwarding ordinary input props/ref and owning reveal state. Profile can adopt the password widget if password reveal is desired there.

**Keep distinct:** schemas, password requirements, confirm-password rules, autocomplete values, mutations, errors, and post-submit routes. Login must not inherit registration's minimum-length validation.

**Validate:** reveal button does not submit the form, accessible reveal/hide label, form ref/error integration, independent reveal state, and `current-password`/`new-password` autocomplete. Do not create one mode-driven login/register/password-change form.

### E11. Diff navigation and hidden-range controls

**Evidence:** [DiffViewer](../apps/web/src/domain/compare/snapshots/components/diff-viewer.tsx) and [FileComparison](../apps/web/src/domain/compare/snapshots/components/file-comparison.tsx) repeat next/previous wrapping navigation, temporary highlighting, range expansion state, range merging, context-window logic, and “All / Top / Bottom” hidden-line controls. `ExpandUnchangedControl` and `InlineDiffText` are already shared.

**Proposal:** share the collapsed-range controls first, then identical range helpers in the snapshot domain. A small navigation hook can follow if it takes change indexes and row refs without owning either renderer.

**Keep distinct:** unified lines use `add`/`remove`/`unchanged`; side-by-side rows use `added`/`removed`/`changed`/`same`. Each renderer owns its row types, number columns, intraline pairing, and stats. Content-dependent state reset is essential.

**Validate:** no changes, one change, first/last wrapping, partial/full expansion, overlapping ranges, correct original-index scrolling, and changing either file. Existing diff tests cover underlying algorithms, not necessarily all component navigation behavior.

### E12. Sortable metric order list

**Evidence:** `SortableDisplayMetricRow` and DnD setup in [DisplayMetricsForm](../apps/web/src/domain/projects/components/settings/display-metrics-form.tsx) overlap with `SortableMetricRow`/`MetricsOrderList` in [metrics order list](../apps/web/src/app/(core)/projects/[projectId]/metrics/components/metrics-order-list.tsx).

**Proposal:** a small metric-order list with stable IDs and a row-content slot. Reuse the installed DnD kit and its `arrayMove`; the caller maps reordered IDs back to its own entries.

**Keep distinct:** settings entries use name plus label and can include legacy string entries; project metrics columns are names within a selected label. Settings also show direction icons and control display membership. Do not reduce all IDs to displayed text.

**Validate:** duplicate metric names under different labels, disabled state, missing drag target, unchanged drops, and correct payload ordering. Table-row drag and kanban cross-column movement should keep their own DnD composition.

### E13. Experiment summary, status, and progress fragments

**Evidence:** [KanbanCard](../apps/web/src/domain/experiments/components/kanban/kanban-card.tsx) and [KanbanCardOverlay](../apps/web/src/domain/experiments/components/kanban/kanban-card-overlay.tsx) duplicate color/name/description/short-ID content. Sidebar and details metadata duplicate status selects and created/started fields. Sidebar and kanban repeat running progress presentation.

**Proposal:** `KanbanCardContent` for the card/drag overlay; a small `ExperimentStatusSelect` for sidebar/details; and `ExperimentProgress` for sidebar/kanban, optionally using existing `Progress`. A metadata date block can be shared if it stays cohesive. These can stay in the experiment domain.

**Keep distinct:** drag wrappers, overlay rotation/width, selection styling, running-only visibility, and immediate status mutation versus saved draft fields. DAG nodes and recent experiment rows need different content and interactions.

**Validate:** long text, identical card/overlay content, progress/status transitions, date formatting, and pending mutations. A universal `EntityCard` or one component with table/kanban/DAG/recent modes would likely cost more than it saves.

### E14. Page-local blocks that can become domain components

These are useful organization proposals, but **not demonstrated cross-page reuse**. Move them only when their separation helps maintenance or a second consumer actually appears.

| Existing block | Suggested extraction | Limits |
| --- | --- | --- |
| `DynamicSettingsEditor` in [settings page](../apps/web/src/app/(core)/projects/[projectId]/settings/page.tsx), around line 344 | `domain/projects/components/settings/project-custom-settings-editor.tsx` | Already a component in the page file. Preserve the key-driven draft reset, typed parsing, and existing save/rename semantics; moving it does not fix them |
| Members JSX in [team detail](../apps/web/src/app/(core)/(workspace)/teams/[teamId]/page.tsx) | `TeamMembersPanel`, parallel to existing `ProjectMembersPanel` | Compose E3's shared controls; keep team rules and team mutations |
| User/project/team tables in [admin page](../apps/web/src/app/admin/page.tsx) | Admin-local table components | Keep user draft/save state and project transfer operations local to admin; reuse E5 rather than introduce a schema-driven CRUD system |
| Token creation form, created-token/setup block, token list in [API tokens](../apps/web/src/app/(core)/profile/api-tokens/page.tsx) | API-token-domain components | Created token is shown once; preserve transient secret state and revoke flow |
| Account and password forms in [profile](../apps/web/src/app/(core)/profile/page.tsx) | Auth/profile-local form components | Separate pending state and password-only payload/reset behavior |
| Inline team card in [teams list](../apps/web/src/app/(core)/(workspace)/teams/page.tsx) | `TeamCard` | One demonstrated consumer; defer if the current local JSX is easy to maintain |
| Report rows in [report list](../apps/web/src/app/(core)/projects/[projectId]/reports/page.tsx) | `ReportListItem` | One demonstrated consumer; keep deletion confirmation outside the row |

Page-local helpers such as `InfoRow` on About and `CollapsibleProjectBucket`/`ProjectGrid` on Projects already have sensible local boundaries. They do not need promotion to the shared layer solely because they are reusable in theory.

### E15. File previews: selective reuse, not one file-browser engine

**Evidence:** named artifacts use `StructuredArtifactPreview`; snapshot inspection uses `FileViewer`, `DiffViewer`, and `FileComparison`; hparams use a separate recursive JSON tree. Named artifact fullscreen lives in [FinalArtifactCard](../apps/web/src/domain/experiment-artifacts/components/final-artifact-card.tsx), while step-image expansion uses `ImagePreviewDialog`.

**Proposal:** if consistent file inspection is desired, add a text-preview mode to the existing preview presentation or adapt already-loaded snapshot text to it. Share a simple image presentation/expand action only when both consumers want the same controls. For trees, consider extracting `StructuredNode` as a read-only tree before modifying the much richer hparams tree.

**Keep distinct:** snapshot code view/diff, artifact format/status dispatch, hparams copy-path/diff actions, and fullscreen-specific footer controls. Hparams root is an object and its tree collapses differently; YAML/TOML can produce values beyond an identical JSON-tree contract. Uploaded Markdown and authored docs also have distinct pipelines.

**Validate:** root arrays/scalars/null, invalid JSON/YAML/TOML, binary/too-large/decode errors, long content, syntax highlighting, image controls, and preview loading. This is a product consistency option, not a confirmed need for a generic tree or preview framework.

## Supporting reuse that belongs in helpers/hooks, not components

| Evidence | Proposal | Caution |
| --- | --- | --- |
| `adminFetch`, `adminBaseUrl`, and the admin storage key in [admin](../apps/web/src/app/admin/page.tsx) and [storage](../apps/web/src/app/admin/storage/page.tsx) | One admin-specific request helper and storage-key constant | Preserve the admin key override used during probing. Ordinary Axios client attaches user auth and clears it on 401; it is not automatically the right admin client |
| Admin probes/invalidates a stored key; storage page reads it in requests | Optionally reuse an admin gate/session hook across both | This changes storage-page entry/error behavior. Confirm intended UX; shared transport alone does not require a gate |
| Storage's local `formatBytes` duplicates [format-storage-usage](../apps/web/src/lib/format-storage-usage.ts) | Import existing `formatBytes` | Straight reuse; no `StorageFormatter` abstraction needed |
| `triggerDownload` in [metrics export](../apps/web/src/app/(core)/projects/[projectId]/metrics/lib/export-report.ts) duplicates blob/anchor handling in [downloads](../apps/web/src/lib/downloads.ts) | Reuse `downloadBlob(new Blob(...), filename)` | Preserve CSV BOM, MIME type, export column/row ordering, and file naming |
| Dates are formatted directly across sidebar/details/cards/profile | Reuse [formatLocalDateTime](../apps/web/src/lib/format-local-datetime.ts) where its contract fits | Missing/invalid handling and exact date format are caller decisions; do not force relative and absolute dates to match |
| Experiment lists already route through [useExperiments](../apps/web/src/domain/experiments/hooks/experiments-hook.ts) | Continue reusing its pagination/search/polling options | Server-filtered search, loaded-data filtering, auto pagination, and scroll pagination differ; a shared search box must not hide that |
| Scalars/artifacts live hooks already share query keys and [incremental helpers](../apps/web/src/domain/scalars/utils/incremental-refresh.ts) | Preserve existing reuse | Their baseline and merge behavior differs. Do not replace both with a generic polling/cache-merging engine |
| [Metric formatting](../apps/web/src/lib/metrics/metric-value-display.ts), metric identity/labels, [column width policy](../apps/web/src/lib/table/column-width-policy.ts), and [inference](../apps/web/src/lib/table/column-width-inference.ts) already exist | Reuse them for new displays/table implementations | Similar table chrome does not imply identical table data models, resize lifecycle, or persisted keys |
| Three [artifact Route Handlers](../apps/web/src/app/api/experiment-artifacts) repeat cookie auth, no-store upstream fetch, and some named URL construction | If touching them together, consider one narrow server-only fetch/URL helper | Streaming download, bounded preview reading, disposition, query validation, and error response formats must remain route-specific |

## Coverage by page area

This maps every page entry point to the relevant reuse conclusion. Paths are browser routes; `:projectId`, `:teamId`, and similar names denote dynamic segments.

| Pages | Reuse/extraction assessment |
| --- | --- |
| `/` | Auth-dependent redirect plus existing `Skeleton`; no worthwhile component extraction |
| `/login`, `/register` | E10 auth presentation/password control; keep separate validation and submit behavior |
| `/projects` | Already uses `PageHeader`, `ProjectCard`, creation modals, skeleton/empty states, workspace actions; local grouped-list helpers can remain local |
| `/teams` | Existing shared states/create modal; optional `TeamCard`, with no second consumer proven |
| `/teams/:teamId` | E3 member controls, E14 `TeamMembersPanel`, existing `TeamDangerZone`; do not merge project permissions |
| `/projects/:projectId` | Already composed from dashboard/stat/recent/status cards and `EntityIdDisplay`; share experiment summary pieces selectively |
| `/projects/:projectId/experiments` | Existing table frame, selection/bar, inspector, create dialog; E2 parent control, E13 summary/status, shared no-project/refresh presentation |
| `/projects/:projectId/kanban` | Existing board/inspector; E13 card/overlay/progress fragments; retain cross-column drag behavior |
| `/projects/:projectId/dag` | Existing inspector/ordered selection/metric diff rendering; retain graph layout, cycle checks, zoom-aware node resizing |
| `/projects/:projectId/experiments/details` | Already shares editor, logged metrics, hparams, features, artifacts; E2/E13 remove remaining metadata duplication |
| `/projects/:projectId/experiments/:experimentId/artifacts` | Redirect to details; no independent artifact screen to refactor |
| `/projects/:projectId/metrics` | Already split into page state, control panel, toolbar, table parts, frame, and inspector; E12 metric order list; reuse export helpers |
| `/projects/:projectId/scalars` | Already split into data/query/live state hooks, content/grid/cards, sidebars, dialogs, media; E6/E7 reduce repeated controls; retain URL state and incremental refresh |
| `/projects/:projectId/compare` | Existing shell, experiment picker, data compare table, scalar chart, snapshot widgets; E1/E6/E11 are strongest remaining extractions |
| `/projects/:projectId/settings` | Existing basic/display/metric/member/danger components; E3/E4/E12 and optional custom-settings move |
| `/projects/:projectId/hypotheses` | Existing list/card/dialog/status components; reuse no-project state; no universal experiment/hypothesis editor |
| `/projects/:projectId/reports` | Shared page states, E4 confirmation, optional row component |
| `/projects/:projectId/reports/:reportId` | Existing `SimpleReportEditor`; keep report draft/save lifecycle separate; reuse small loading/error presentation if needed |
| `/profile` | E9 ID/copy reuse, E10 optional password reveal, E14 optional form split |
| `/profile/password` | Redirect to profile; no standalone password form to consolidate |
| `/profile/api-tokens` | E4 confirmation, E9 clipboard, E14 optional token panels; preserve one-time token handling |
| `/about` | Existing header/cards and small local `InfoRow`; no major extraction justified |
| `/admin`, `/admin/storage` | E5 pagination, existing header reuse, admin transport/key helper, existing byte formatting, optional local table/gate components |
| `/docs`, `/docs/[...path]` | Already shared docs page shell/index/Markdown/topic navigation; preserve document pipeline; no frontend-wide Markdown unification |

## Apparent legacy or currently unconsumed components

Import/symbol searches found no active render callers for the following candidates. This is **not proof of dead code**: exports, aliases, external consumers, unfinished work, and planned features need human validation.

| Candidate | Evidence and recommendation |
| --- | --- |
| [ScalarsControlsPanel](../apps/web/src/domain/scalars/components/scalars-controls-panel.tsx) | Exported through the scalars barrel, but no render caller found. Current route uses the split view-settings components. Do not extend both implementations |
| [ScalarViewsSidebar](../apps/web/src/domain/scalars/components/scalar-views-sidebar.tsx) | Barrel export but no render caller found; current settings sidebar uses `ScalarSavedViewsSection`. If retained, compose that section rather than maintain parallel rename/list logic |
| [CodeViewer](../apps/web/src/domain/compare/snapshots/components/code-viewer.tsx) | No import/render caller found; active single-file view uses `FileViewer`. Prefer the active component for new reuse |
| [FileUpload01](../apps/web/src/components/shared/file-upload/index.tsx) | No consumer found. It simulates random upload progress and is not the production upload contract. Reuse `FileDropzone`/hook instead |
| [RecentHypothesesCard](../apps/web/src/domain/projects/components/recent-hypotheses-card.tsx) | Dashboard import/render are commented out; barrel export remains. A proposed shared “recent items” card would currently have only one active domain consumer |

No deletions are proposed as certain, and none were made.

## What should remain separate

1. **Aggregate metric plots and scalar curves.** Recharts aggregate plots and Plotly scalar series have different axes/data/interaction contracts. Share controls and existing resize pieces, not a mode-heavy `UniversalChart`.
2. **Experiment table, metric pivot, compare table, kanban, and DAG.** Reuse shells, formatting, selection, and text. Keep their data shape, sorting, drag, and layout behavior distinct.
3. **Named experiment artifacts, step-logged objects, and project CAS.** Share file selection/preview presentation where compatible; preserve endpoint and metadata semantics. This review did not find a standalone project-CAS upload page that needs a new UI component.
4. **Project/team permission mutations.** Shared member UI must receive capabilities and handlers; it must not infer or flatten inherited/override/direct access.
5. **Auth forms and domain creation forms.** Existing `Form`, `Input`, `Textarea`, `Dialog`, and schemas already provide much of the reuse. Similar name/description fields do not justify a generic entity form builder.
6. **Docs Markdown, uploaded Markdown, report rich text, and feature trees.** Keep sanitization and data-model boundaries. Any docs-rendering change must follow the repository's [doc-pipeline guidance](../apps/web/content/docs/contributing/extending-doc-pipeline.md).
7. **Persistence and refresh.** Retain project/label/tab-specific storage keys, URL codecs, loaded-page semantics, and domain-specific cache merges. Shared UI need not own them.

## Suggested validation and adoption sequence

1. Validate the smallest visible duplicates first: E1 pickers, E5 admin pagination, and E6 slider controls. Choose the intended behavior before sharing it.
2. Validate E2/E3/E4 with domain examples: parent drafts/inheritance, project role overrides, and async cleanup failures. These give more reuse but carry more behavioral constraints.
3. Address E7/E8 only with a browser comparison of full-height layouts and narrow viewports. Keep shell changes separate from unrelated data changes.
4. Adopt E9–E13 where they remove active duplication. Defer E14/E15 unless maintenance or a second consumer justifies them.
5. For each approved change, migrate two real consumers before declaring the abstraction useful. If the second consumer needs many unrelated options, narrow or abandon the extraction.

For implementation validation, use the frontend's existing pnpm checks (`pnpm run check-types`, `pnpm run lint`, and relevant `pnpm run test` cases from `apps/web`) plus a focused browser check of the changed interaction. Add a small behavior test for new shared logic rather than broad tests that merely repeat its JSX. Existing tests cover metric formatting, selections/URL state, scalar merging/layout, feature/hparams diffs, and snapshot diff algorithms; they do not demonstrate every proposed UI migration is safe.

**Report validation:** recommendations were checked against local callers and source, and source links were checked for existence. The application was not run, and no runtime tests were needed for this documentation-only addition. Human validation remains necessary before any implementation.
