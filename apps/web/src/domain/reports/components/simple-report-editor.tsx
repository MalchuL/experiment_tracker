"use client";

import { EditorContent, useEditor } from "@tiptap/react";
import StarterKit from "@tiptap/starter-kit";
import type { ReportDocumentJSON } from "../types";

type SimpleReportEditorProps = {
  documentJson: ReportDocumentJSON;
  onDocumentChange?: (doc: ReportDocumentJSON) => void;
  /** When this changes, the editor is recreated with `documentJson`. */
  editorKey: string;
};

export function SimpleReportEditor({
  documentJson,
  onDocumentChange,
  editorKey,
}: SimpleReportEditorProps) {
  const editor = useEditor(
    {
      extensions: [StarterKit],
      content: documentJson,
      immediatelyRender: false,
      editorProps: {
        attributes: {
          class:
            "min-h-[240px] max-w-none rounded-md border border-input bg-background px-3 py-2 text-sm shadow-sm focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring [&_.ProseMirror]:min-h-[200px]",
        },
      },
      onUpdate: ({ editor: ed }) => {
        onDocumentChange?.(ed.getJSON() as ReportDocumentJSON);
      },
    },
    [editorKey],
  );

  return <EditorContent editor={editor} />;
}
