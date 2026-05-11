"use client";

import type { Editor } from "@tiptap/core";
import {
  Bold,
  Heading1,
  Heading2,
  Heading3,
  Italic,
  List,
  ListOrdered,
  Minus,
  Package,
  Strikethrough,
  Activity,
  LineChart,
  Quote,
  Redo2,
  Underline as UnderlineIcon,
  Undo2,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Separator } from "@/components/ui/separator";
import {
  defaultArtifactEmbedAttrs,
  defaultMetricEmbedAttrs,
  defaultScalarEmbedAttrs,
} from "./embed-blocks/types";

export interface ReportEditorToolbarProps {
  editor: Editor;
}

export function ReportEditorToolbar({ editor }: ReportEditorToolbarProps) {
  const chain = () => editor.chain().focus();

  return (
    <div className="flex flex-wrap items-center gap-0.5 border-b border-border bg-muted/40 px-2 py-1.5">
      <Button
        type="button"
        size="sm"
        variant="ghost"
        className="h-8 w-8 p-0"
        onClick={() => chain().undo().run()}
        disabled={!editor.can().undo()}
        aria-label="Undo"
      >
        <Undo2 className="h-4 w-4" />
      </Button>
      <Button
        type="button"
        size="sm"
        variant="ghost"
        className="h-8 w-8 p-0"
        onClick={() => chain().redo().run()}
        disabled={!editor.can().redo()}
        aria-label="Redo"
      >
        <Redo2 className="h-4 w-4" />
      </Button>
      <Separator orientation="vertical" className="mx-1 h-6" />
      <Button
        type="button"
        size="sm"
        variant={editor.isActive("heading", { level: 1 }) ? "secondary" : "ghost"}
        className="h-8 w-8 p-0"
        onClick={() => chain().toggleHeading({ level: 1 }).run()}
        aria-label="Heading 1"
      >
        <Heading1 className="h-4 w-4" />
      </Button>
      <Button
        type="button"
        size="sm"
        variant={editor.isActive("heading", { level: 2 }) ? "secondary" : "ghost"}
        className="h-8 w-8 p-0"
        onClick={() => chain().toggleHeading({ level: 2 }).run()}
        aria-label="Heading 2"
      >
        <Heading2 className="h-4 w-4" />
      </Button>
      <Button
        type="button"
        size="sm"
        variant={editor.isActive("heading", { level: 3 }) ? "secondary" : "ghost"}
        className="h-8 w-8 p-0"
        onClick={() => chain().toggleHeading({ level: 3 }).run()}
        aria-label="Heading 3"
      >
        <Heading3 className="h-4 w-4" />
      </Button>
      <Separator orientation="vertical" className="mx-1 h-6" />
      <Button
        type="button"
        size="sm"
        variant={editor.isActive("bold") ? "secondary" : "ghost"}
        className="h-8 w-8 p-0"
        onClick={() => chain().toggleBold().run()}
        aria-label="Bold"
      >
        <Bold className="h-4 w-4" />
      </Button>
      <Button
        type="button"
        size="sm"
        variant={editor.isActive("italic") ? "secondary" : "ghost"}
        className="h-8 w-8 p-0"
        onClick={() => chain().toggleItalic().run()}
        aria-label="Italic"
      >
        <Italic className="h-4 w-4" />
      </Button>
      <Button
        type="button"
        size="sm"
        variant={editor.isActive("underline") ? "secondary" : "ghost"}
        className="h-8 w-8 p-0"
        onClick={() => chain().toggleUnderline().run()}
        aria-label="Underline"
      >
        <UnderlineIcon className="h-4 w-4" />
      </Button>
      <Button
        type="button"
        size="sm"
        variant={editor.isActive("strike") ? "secondary" : "ghost"}
        className="h-8 w-8 p-0"
        onClick={() => chain().toggleStrike().run()}
        aria-label="Strikethrough"
      >
        <Strikethrough className="h-4 w-4" />
      </Button>
      <Separator orientation="vertical" className="mx-1 h-6" />
      <Button
        type="button"
        size="sm"
        variant={editor.isActive("bulletList") ? "secondary" : "ghost"}
        className="h-8 w-8 p-0"
        onClick={() => chain().toggleBulletList().run()}
        aria-label="Bullet list"
      >
        <List className="h-4 w-4" />
      </Button>
      <Button
        type="button"
        size="sm"
        variant={editor.isActive("orderedList") ? "secondary" : "ghost"}
        className="h-8 w-8 p-0"
        onClick={() => chain().toggleOrderedList().run()}
        aria-label="Numbered list"
      >
        <ListOrdered className="h-4 w-4" />
      </Button>
      <Button
        type="button"
        size="sm"
        variant={editor.isActive("blockquote") ? "secondary" : "ghost"}
        className="h-8 w-8 p-0"
        onClick={() => chain().toggleBlockquote().run()}
        aria-label="Quote"
      >
        <Quote className="h-4 w-4" />
      </Button>
      <Button
        type="button"
        size="sm"
        variant="ghost"
        className="h-8 w-8 p-0"
        onClick={() => chain().setHorizontalRule().run()}
        aria-label="Divider"
      >
        <Minus className="h-4 w-4" />
      </Button>
      <Separator orientation="vertical" className="mx-1 h-6" />
      <Button
        type="button"
        size="sm"
        variant="outline"
        className="h-8 gap-1 px-2 text-xs"
        onClick={() =>
          chain()
            .insertContent({
              type: "metricEmbed",
              attrs: defaultMetricEmbedAttrs(),
            })
            .run()
        }
      >
        <LineChart className="h-3.5 w-3.5" />
        Metrics
      </Button>
      <Button
        type="button"
        size="sm"
        variant="outline"
        className="h-8 gap-1 px-2 text-xs"
        onClick={() =>
          chain()
            .insertContent({
              type: "scalarEmbed",
              attrs: defaultScalarEmbedAttrs(),
            })
            .run()
        }
      >
        <Activity className="h-3.5 w-3.5" />
        Scalars
      </Button>
      <Button
        type="button"
        size="sm"
        variant="outline"
        className="h-8 gap-1 px-2 text-xs"
        onClick={() =>
          chain()
            .insertContent({
              type: "artifactEmbed",
              attrs: defaultArtifactEmbedAttrs(),
            })
            .run()
        }
      >
        <Package className="h-3.5 w-3.5" />
        Artifacts
      </Button>
    </div>
  );
}
