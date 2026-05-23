# Stage 1: Notion-Like Report Editor

## Summary
Upgrade `SimpleReportEditor` into a Notion-style Tiptap report editor using official Tiptap features/components first. Reports continue storing Tiptap JSON in the existing `content` field; no backend or database changes.

Use Tiptap UI components for slash commands: `SlashCommandTriggerButton` for inserting `/`, and `SlashDropdownMenu` for the command palette when available through the Tiptap CLI/component install path. Tiptap documents these as separate UI components. 

## Key Changes
- Add required Tiptap editor packages/components:
  - official drag handle extension: `@tiptap/extension-drag-handle`
  - Tiptap UI slash components: `SlashCommandTriggerButton` and `SlashDropdownMenu`
  - any small peer dependencies required by those generated components
- Keep persistence unchanged:
  - editor loads `documentJson`
  - emits `onDocumentChange(ed.getJSON())`
  - existing Save button persists the report
- Improve editor surface:
  - document-like writing area
  - clear styles for headings, lists, quote, code block, divider, and selection
  - maintain existing manual save flow
- Add built-in/block commands first:
  - Text
  - Heading 1/2/3
  - Bullet list
  - Numbered list
  - Quote
  - Code block
  - Divider
  - Clear formatting
- Add slash command UX:
  typing `/` opens the slash dropdown
  - toolbar/button can insert the slash trigger
  - keyboard navigation works through the menu
  - commands transform the current block or insert the selected block type
- Add block drag UX:
  - use Tiptap’s official drag handle extension
  - show a compact grip handle beside blocks
  - support top-level block movement first
  - enable nested dragging only if it works cleanly with lists/quotes
- Add a small inline formatting bubble menu:
  - bold
  - italic
  - strike
  - inline code
  - clear formatting

## Later Stages
- Stage 2: block action menu with duplicate, delete, turn into, insert block.
- Stage 3: task lists, links, tables, images, and better placeholders.
- Stage 4: experiment-tracker blocks such as metric chart, experiment summary, artifact preview, and run comparison.

## Test Plan
- Run the web lint/typecheck command available in `apps/web`.
- Run web tests if the existing test script is available.
- Manually verify:
  - existing reports load without migration
  - edits update JSON and save/reload correctly
  - slash menu opens from typing `/` and from the trigger button
  - all Stage 1 commands work
  - block drag reorders paragraphs, headings, lists, quotes, code blocks, and dividers
  - bubble menu formats selected text
  - undo/redo, Enter, Backspace, and markdown shortcuts still behave normally

## Assumptions
- It is acceptable to add official Tiptap packages/components to `apps/web`.
- If Tiptap UI slash components cannot be installed cleanly, implementation should stop and report the incompatibility instead of silently replacing them with a custom slash menu.
- No custom ML/report blocks are included in Stage 1.
