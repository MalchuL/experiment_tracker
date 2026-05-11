"use client";

import Link from "@tiptap/extension-link";
import Placeholder from "@tiptap/extension-placeholder";
import TaskItem from "@tiptap/extension-task-item";
import TaskList from "@tiptap/extension-task-list";
import Underline from "@tiptap/extension-underline";
import { EditorContent, useEditor } from "@tiptap/react";
import StarterKit from "@tiptap/starter-kit";
import { useEffect } from "react";
import { ReportEditorProvider, type ReportEditorExperimentOption } from "./report-editor-context";
import {
  ArtifactEmbedExtension,
  MetricEmbedExtension,
  ScalarEmbedExtension,
} from "./extensions";
import { ReportEditorToolbar } from "./report-editor-toolbar";

const editorExtensions = [
  StarterKit.configure({
    heading: { levels: [1, 2, 3] },
    bulletList: { keepMarks: true, keepAttributes: false },
    orderedList: { keepMarks: true, keepAttributes: false },
  }),
  Placeholder.configure({
    placeholder:
      "Write a report… Use the toolbar to insert metric, scalar, or artifact blocks.",
  }),
  Underline,
  Link.configure({ openOnClick: false, autolink: true, defaultProtocol: "https" }),
  TaskList,
  TaskItem.configure({ nested: true }),
  MetricEmbedExtension,
  ScalarEmbedExtension,
  ArtifactEmbedExtension,
];

const editorPropsClass =
  "min-h-[420px] max-w-none px-4 py-4 text-sm leading-relaxed outline-none " +
  "[&_p]:my-2 [&_ul]:my-2 [&_ol]:my-2 [&_li]:my-0.5 [&_h1]:mt-6 [&_h1]:mb-2 [&_h1]:text-2xl [&_h1]:font-semibold " +
  "[&_h2]:mt-5 [&_h2]:mb-2 [&_h2]:text-xl [&_h2]:font-semibold [&_h3]:mt-4 [&_h3]:mb-1.5 [&_h3]:text-lg [&_h3]:font-semibold " +
  "[&_blockquote]:border-l-2 [&_blockquote]:border-muted-foreground/30 [&_blockquote]:pl-3 [&_blockquote]:italic " +
  "[&_a]:text-primary [&_a]:underline [&_pre]:rounded-md [&_pre]:bg-muted [&_pre]:p-3";

export interface ReportRichTextEditorProps {
  projectId: string;
  experiments: ReportEditorExperimentOption[];
  /** Document at mount; remount the editor (e.g. `key={reportId}`) when replacing from the server. */
  initialContent: Record<string, unknown>;
  onChange: (json: Record<string, unknown>) => void;
  editable?: boolean;
}

export function ReportRichTextEditor({
  projectId,
  experiments,
  initialContent,
  onChange,
  editable = true,
}: ReportRichTextEditorProps) {
  const editor = useEditor({
    immediatelyRender: false,
    extensions: editorExtensions,
    content: initialContent,
    editable,
    editorProps: {
      attributes: {
        class: editorPropsClass,
      },
    },
    onUpdate: ({ editor: ed }) => {
      onChange(ed.getJSON() as Record<string, unknown>);
    },
  });

  useEffect(() => {
    editor?.setEditable(editable);
  }, [editor, editable]);

  return (
    <ReportEditorProvider projectId={projectId} experiments={experiments}>
      <div className="overflow-hidden rounded-md border border-border bg-background">
        {editor ? <ReportEditorToolbar editor={editor} /> : null}
        {editor ? <EditorContent editor={editor} /> : (
          <div className="min-h-[420px] animate-pulse bg-muted/40" aria-hidden />
        )}
      </div>
    </ReportEditorProvider>
  );
}
