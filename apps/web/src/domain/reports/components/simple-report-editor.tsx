"use client";

import { offset } from "@floating-ui/dom";
import DragHandle, {
  type DragHandleProps,
} from "@tiptap/extension-drag-handle-react";
import NodeRange from "@tiptap/extension-node-range";
import Placeholder from "@tiptap/extension-placeholder";
import type { Node as PMNode } from "@tiptap/pm/model";
import { BubbleMenu } from "@tiptap/react/menus";
import StarterKit from "@tiptap/starter-kit";
import { type Editor, Tiptap, useEditor } from "@tiptap/react";
import { useCallback, useRef } from "react";
import {
  Bold,
  Code,
  GripVertical,
  Italic,
  RemoveFormatting,
  Strikethrough,
} from "lucide-react";
import {
  SlashDropdownMenu,
  type SlashMenuItemType,
} from "@/components/tiptap-ui/slash-dropdown-menu";
import type { ReportDocumentJSON } from "../types";

type SimpleReportEditorProps = {
  documentJson: ReportDocumentJSON;
  onDocumentChange?: (doc: ReportDocumentJSON) => void;
  /** When this changes, the editor is recreated with `documentJson`. */
  editorKey: string;
};

const slashItems: SlashMenuItemType[] = [
  "text",
  "heading_1",
  "heading_2",
  "heading_3",
  "bullet_list",
  "ordered_list",
  "quote",
  "code_block",
  "divider",
];

type ReportDragHandleNested = Extract<
  NonNullable<DragHandleProps["nested"]>,
  object
>;

/**
 * Nested drag handle + gutter-aligned edge scoring (negative threshold = zone just
 * outside the block edge). Use `REPORT_DRAG_HANDLE_NESTED_BY_DIR.ltr` / `.rtl` by document direction.
 */
const NESTED_CONFIG_LTR: ReportDragHandleNested = {
  edgeDetection: { threshold: -16, edges: ["left"] },
};

const NESTED_CONFIG_RTL: ReportDragHandleNested = {
  edgeDetection: { threshold: -16, edges: ["right"] },
};

/** Pick `.rtl` when the editor shell uses `dir="rtl"` (see `NESTED_CONFIG_*` above). */
const REPORT_DRAG_HANDLE_NESTED_BY_DIR = {
  ltr: NESTED_CONFIG_LTR,
  rtl: NESTED_CONFIG_RTL,
};

/** Stable references — inline objects in BubbleMenu/DragHandle deps cause update loops with `shouldRerenderOnTransaction`. */
const BUBBLE_MENU_OPTIONS = { placement: "top" as const };

const DRAG_HANDLE_COMPUTE_POSITION_CONFIG = {
  middleware: [offset({ mainAxis: 1, crossAxis: 4 })],
};

const SLASH_MENU_CONFIG = {
  enabledItems: slashItems,
  showGroups: true,
};

const REPORT_EDITOR_SLASH_HINT = "Type / for commands";

/** Insert after the innermost enclosing list item so we add a sibling row, not a second block inside the item. */
function getInsertPosBelowTargetBlock(
  doc: PMNode,
  pos: number,
  node: PMNode,
): number {
  const $pos = doc.resolve(pos);
  for (let d = $pos.depth; d > 0; d -= 1) {
    const n = $pos.node(d);
    if (n.type.name === "listItem") {
      return $pos.before(d) + n.nodeSize;
    }
  }
  return pos + node.nodeSize;
}

function getBlockInsertContent(
  editor: Editor,
  insertPos: number,
):
  | { type: "listItem"; content: { type: "paragraph" }[] }
  | { type: "paragraph" } {
  const { doc, schema } = editor.state;
  let $pos;
  try {
    $pos = doc.resolve(insertPos);
  } catch {
    return { type: "paragraph" };
  }
  const parent = $pos.parent;
  if (
    (parent.type.name === "bulletList" || parent.type.name === "orderedList") &&
    schema.nodes.listItem
  ) {
    return { type: "listItem", content: [{ type: "paragraph" }] };
  }
  return { type: "paragraph" };
}

export function SimpleReportEditor({
  documentJson,
  onDocumentChange,
  editorKey,
}: SimpleReportEditorProps) {
  const editor = useEditor(
    {
      extensions: [
        StarterKit.configure({
          heading: {
            levels: [1, 2, 3],
          },
        }),
        Placeholder.configure({
          placeholder: ({ node }) =>
            node.type.name === "paragraph" || node.type.name === "heading"
              ? REPORT_EDITOR_SLASH_HINT
              : "",
          showOnlyWhenEditable: true,
          showOnlyCurrent: true,
          emptyNodeClass: "is-empty",
          emptyEditorClass: "is-editor-empty",
        }),
        NodeRange.configure({
          depth: 0,
          key: null,
        }),
      ],
      content: documentJson,
      immediatelyRender: false,
      shouldRerenderOnTransaction: true,
      editorProps: {
        attributes: {
          class: "report-editor-content focus-visible:outline-none",
        },
      },
      onUpdate: ({ editor: ed }) => {
        onDocumentChange?.(ed.getJSON() as ReportDocumentJSON);
      },
    },
    [editorKey],
  );

  const dragInsertTargetRef = useRef<{ pos: number; node: PMNode } | null>(
    null,
  );

  const onDragHandleNodeChange = useCallback(
    ({
      node,
      pos,
    }: {
      node: PMNode | null;
      editor: Editor;
      pos: number;
    }) => {
      if (node && pos >= 0) {
        dragInsertTargetRef.current = { pos, node };
      } else {
        dragInsertTargetRef.current = null;
      }
    },
    [],
  );

  const handleInsertBlockBelow = useCallback(() => {
    if (!editor || editor.isDestroyed) return;
    const t = dragInsertTargetRef.current;
    if (!t?.node || t.pos < 0) return;

    const insertAt = getInsertPosBelowTargetBlock(
      editor.state.doc,
      t.pos,
      t.node,
    );
    const content = getBlockInsertContent(editor, insertAt);

    editor
      .chain()
      .focus()
      .insertContentAt(insertAt, content, { updateSelection: true })
      .run();
  }, [editor]);

  return (
    <div className="report-editor-shell">
      {!editor ? (
        <div className="report-editor-canvas">
          <div className="min-h-[320px]" />
        </div>
      ) : (
        <Tiptap editor={editor}>
          <BubbleMenu
            options={BUBBLE_MENU_OPTIONS}
            className="report-editor-bubble-menu"
          >
            <InlineFormatButton
              label="Bold"
              active={editor.isActive("bold")}
              onClick={() => editor.chain().focus().toggleBold().run()}
            >
              <Bold className="h-4 w-4" />
            </InlineFormatButton>
            <InlineFormatButton
              label="Italic"
              active={editor.isActive("italic")}
              onClick={() => editor.chain().focus().toggleItalic().run()}
            >
              <Italic className="h-4 w-4" />
            </InlineFormatButton>
            <InlineFormatButton
              label="Strike"
              active={editor.isActive("strike")}
              onClick={() => editor.chain().focus().toggleStrike().run()}
            >
              <Strikethrough className="h-4 w-4" />
            </InlineFormatButton>
            <InlineFormatButton
              label="Inline code"
              active={editor.isActive("code")}
              onClick={() => editor.chain().focus().toggleCode().run()}
            >
              <Code className="h-4 w-4" />
            </InlineFormatButton>
            <InlineFormatButton
              label="Clear formatting"
              onClick={() =>
                editor.chain().focus().unsetAllMarks().clearNodes().run()
              }
            >
              <RemoveFormatting className="h-4 w-4" />
            </InlineFormatButton>
          </BubbleMenu>

          <SlashDropdownMenu config={SLASH_MENU_CONFIG} />

          <DragHandle
            // @ts-ignore — `locked` is documented on Drag Handle React but omitted from published `DragHandleProps`; needed so the handle does not hide on every keydown while typing.
            locked={true}
            editor={editor}
            nested={REPORT_DRAG_HANDLE_NESTED_BY_DIR.ltr}
            className="report-editor-block-controls"
            computePositionConfig={DRAG_HANDLE_COMPUTE_POSITION_CONFIG}
            onNodeChange={onDragHandleNodeChange}
          >
            <div className="report-editor-block-controls-inner">
              <button
                type="button"
                className="report-editor-insert-button"
                aria-label="Insert block below"
                title="Insert block below"
                onDragStart={(e) => {
                  e.preventDefault();
                  e.stopPropagation();
                }}
                onClick={(e) => {
                  e.preventDefault();
                  e.stopPropagation();
                  handleInsertBlockBelow();
                }}
              >
                +
              </button>
              <div
                className="report-editor-drag-handle"
                role="button"
                tabIndex={-1}
                aria-label="Drag block"
              >
                <GripVertical className="h-4 w-4 shrink-0" strokeWidth={2} />
              </div>
            </div>
          </DragHandle>

          <div className="report-editor-canvas">
            <Tiptap.Content />
          </div>
        </Tiptap>
      )}
    </div>
  );
}

function InlineFormatButton({
  label,
  active,
  onClick,
  children,
}: {
  label: string;
  active?: boolean;
  onClick: () => void;
  children: React.ReactNode;
}) {
  return (
    <button
      type="button"
      className="report-editor-bubble-button"
      data-active={active ? "true" : "false"}
      aria-label={label}
      title={label}
      onClick={onClick}
    >
      {children}
    </button>
  );
}
