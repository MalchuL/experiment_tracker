"use client";

import type { JSONContent, Editor } from "@tiptap/react";
import { Tiptap, useEditor } from "@tiptap/react";
import type { Fragment, Node as ProseMirrorNode, Slice } from "@tiptap/pm/model";
import StarterKit from "@tiptap/starter-kit";
import type { FeatureNode } from "@/lib/features/feature-tree";

type FeatureBulletEditorProps = {
  features: FeatureNode[];
  onChange: (features: FeatureNode[]) => void;
  className?: string;
  wrapperClassName?: string;
};

export function FeatureBulletEditor({
  features,
  onChange,
  className,
  wrapperClassName,
}: FeatureBulletEditorProps) {
  let featureEditor: Editor | null = null;
  const editor = useEditor(
    {
      extensions: [StarterKit],
      content: featureNodesToTiptapDoc(features),
      immediatelyRender: false,
      editorProps: {
        attributes: {
          class:
            className ??
            "h-full min-h-0 overflow-auto rounded border border-input bg-background px-3 py-2 text-sm focus-visible:outline-none [&_ul]:list-disc [&_ul]:pl-5 [&_li]:my-1 [&_p]:m-0",
        },
        clipboardTextSerializer: (slice: Slice): string => serializeSliceToIndentedText(slice),
        handleKeyDown: (_view, event): boolean => {
          if (event.key === "Tab") {
            event.preventDefault();
            if (event.shiftKey) {
              return featureEditor?.commands.liftListItem("listItem") ?? false;
            }
            return featureEditor?.commands.sinkListItem("listItem") ?? false;
          }
          return false;
        },
        handlePaste: (_view, event): boolean => {
          const pastedText = event.clipboardData?.getData("text/plain");
          if (!pastedText || !featureEditor) return false;
          const parsedLines = parseIndentedPastedLines(pastedText);
          if (parsedLines.length === 0) return false;
          if (
            parsedLines.length === 1 &&
            parsedLines[0].depth === 0 &&
            !pastedText.includes("\n")
          ) {
            return false;
          }

          event.preventDefault();
          if (!featureEditor.isActive("listItem")) {
            featureEditor.commands.toggleBulletList();
          }
          featureEditor.commands.insertContent(parsedLines[0].text);
          let currentDepth = parsedLines[0].depth;

          for (const line of parsedLines.slice(1)) {
            featureEditor.commands.splitListItem("listItem");
            if (line.depth > currentDepth) {
              for (let i = 0; i < line.depth - currentDepth; i += 1) {
                featureEditor.commands.sinkListItem("listItem");
              }
            } else if (line.depth < currentDepth) {
              for (let i = 0; i < currentDepth - line.depth; i += 1) {
                featureEditor.commands.liftListItem("listItem");
              }
            }
            featureEditor.commands.insertContent(line.text);
            currentDepth = line.depth;
          }
          return true;
        },
      },
      onUpdate: ({ editor: updatedEditor }) => {
        onChange(tiptapDocToFeatureNodes(updatedEditor.getJSON()));
      },
      onBlur: ({ editor: updatedEditor }) => {
        const currentDoc = updatedEditor.getJSON();
        if (!needsDocNormalization(currentDoc)) return;
        const normalizedDoc = normalizeDocToSingleBulletList(currentDoc);
        updatedEditor.commands.setContent(normalizedDoc, { emitUpdate: false });
        onChange(tiptapDocToFeatureNodes(normalizedDoc));
      },
    },
    [],
  );
  featureEditor = editor;

  if (!editor) {
    return <div className="min-h-0 flex-1 rounded border border-input bg-background" />;
  }

  return (
    <div className={wrapperClassName ?? "min-h-0 flex-1"}>
      <Tiptap editor={editor}>
        <Tiptap.Content />
      </Tiptap>
    </div>
  );
}

function featureNodesToTiptapDoc(features: FeatureNode[]): JSONContent {
  if (features.length === 0) {
    return {
      type: "doc",
      content: [
        {
          type: "bulletList",
          content: [{ type: "listItem", content: [{ type: "paragraph" }] }],
        },
      ],
    };
  }

  return {
    type: "doc",
    content: [
      {
        type: "bulletList",
        content: features.map(featureNodeToListItem),
      },
    ],
  };
}

function featureNodeToListItem(feature: FeatureNode): JSONContent {
  return {
    type: "listItem",
    content: [
      {
        type: "paragraph",
        content: feature.name ? [{ type: "text", text: feature.name }] : undefined,
      },
      ...(feature.children?.length
        ? [
            {
              type: "bulletList",
              content: feature.children.map(featureNodeToListItem),
            },
          ]
        : []),
    ],
  };
}

function tiptapDocToFeatureNodes(doc: JSONContent): FeatureNode[] {
  const rootList = doc.content?.find((node) => node.type === "bulletList");
  return rootList ? bulletListToFeatureNodes(rootList) : [];
}

function bulletListToFeatureNodes(list: JSONContent): FeatureNode[] {
  return (list.content ?? [])
    .filter((node) => node.type === "listItem")
    .map(listItemToFeatureNode)
    .filter((node): node is FeatureNode => node != null);
}

function listItemToFeatureNode(item: JSONContent): FeatureNode | null {
  const paragraph = item.content?.find((node) => node.type === "paragraph");
  const name = textContentFromNode(paragraph).trim();
  if (!name) return null;
  const nestedList = item.content?.find((node) => node.type === "bulletList");
  const children = nestedList ? bulletListToFeatureNodes(nestedList) : [];
  return {
    name,
    ...(children.length ? { children } : {}),
  };
}

function textContentFromNode(node: JSONContent | undefined): string {
  if (!node) return "";
  if (node.type === "text") return node.text ?? "";
  return (node.content ?? []).map(textContentFromNode).join("");
}

function needsDocNormalization(doc: JSONContent): boolean {
  if (doc.type !== "doc") return true;
  const content = doc.content ?? [];
  if (content.length === 0) return true;
  return content.some((node) => node.type !== "bulletList");
}

function normalizeDocToSingleBulletList(doc: JSONContent): JSONContent {
  const rootList = doc.content?.find((node) => node.type === "bulletList");
  const rootListItems = (rootList?.content ?? []).filter((node) => node.type === "listItem");
  const nonListRootItems = (doc.content ?? [])
    .filter((node) => node.type !== "bulletList")
    .map(nodeToListItem)
    .filter((node): node is JSONContent => node != null);
  const normalizedListItems = [...rootListItems, ...nonListRootItems];

  return {
    type: "doc",
    content: [
      {
        type: "bulletList",
        content:
          normalizedListItems.length > 0
            ? normalizedListItems
            : [{ type: "listItem", content: [{ type: "paragraph" }] }],
      },
    ],
  };
}

function nodeToListItem(node: JSONContent): JSONContent | null {
  if (node.type === "listItem") return node;
  const text = textContentFromNode(node).trim();
  if (!text) return null;
  return {
    type: "listItem",
    content: [{ type: "paragraph", content: [{ type: "text", text }] }],
  };
}

function parseIndentedPastedLines(text: string): Array<{ text: string; depth: number }> {
  const rawLines = text.replaceAll("\r\n", "\n").split("\n");
  const parsed = rawLines
    .map(parseIndentedLine)
    .filter((line): line is { text: string; depth: number } => line != null);
  if (parsed.length === 0) return [];

  const minDepth = Math.min(...parsed.map((line) => line.depth));
  return parsed.map((line) => ({ text: line.text, depth: line.depth - minDepth }));
}

function parseIndentedLine(line: string): { text: string; depth: number } | null {
  if (line.trim().length === 0) return null;
  const indentMatch = line.match(/^[\t ]*/);
  const indent = indentMatch?.[0] ?? "";
  const tabCount = Array.from(indent).filter((char) => char === "\t").length;
  const spaceCount = Array.from(indent).filter((char) => char === " ").length;
  const depth = tabCount + Math.floor(spaceCount / 2);
  const text = line.trimStart().replace(/^[-*]\s+/, "").trim();
  if (!text) return null;
  return { text, depth };
}

function serializeSliceToIndentedText(slice: Slice): string {
  const lines: string[] = [];
  serializeFragmentToIndentedLines(slice.content, 0, lines);
  return lines.join("\n");
}

function serializeFragmentToIndentedLines(
  fragment: Fragment,
  depth: number,
  lines: string[],
): void {
  fragment.forEach((node) => serializeNodeToIndentedLines(node, depth, lines));
}

function serializeNodeToIndentedLines(
  node: ProseMirrorNode,
  depth: number,
  lines: string[],
): void {
  if (node.type.name === "bulletList") {
    node.forEach((child) => serializeNodeToIndentedLines(child, depth, lines));
    return;
  }

  if (node.type.name === "listItem") {
    let text = "";
    const nestedLists: ProseMirrorNode[] = [];

    node.forEach((child) => {
      if (child.type.name === "bulletList") {
        nestedLists.push(child);
        return;
      }
      if (text.length === 0) {
        text = child.textContent.trim();
      }
    });

    if (text.length > 0) {
      lines.push(`${"  ".repeat(depth)}${text}`);
    }
    nestedLists.forEach((list) => serializeNodeToIndentedLines(list, depth + 1, lines));
    return;
  }

  if (node.isTextblock) {
    const text = node.textContent.trim();
    if (text.length > 0) {
      lines.push(`${"  ".repeat(depth)}${text}`);
    }
  }
}
