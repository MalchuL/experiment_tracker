"use client";

import { ChevronDown, ChevronRight } from "lucide-react";
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from "@/components/ui/collapsible";
import { parse as parseToml } from "toml";
import { parse as parseYaml } from "yaml";
import { isMarkdownFilepath, MarkdownPreview } from "@/components/shared/markdown-preview";
import type { NamedArtifactPreview } from "@/domain/experiment-artifacts/types";

const STRUCTURED_EXTENSIONS = new Set(["json", "yaml", "yml", "toml"]);

function getExtension(filepath: string): string {
  return filepath.split(".").pop()?.toLowerCase() ?? "";
}

function tryParseStructured(filepath: string, text: string): unknown | null {
  const extension = getExtension(filepath);
  if (!STRUCTURED_EXTENSIONS.has(extension)) {
    return null;
  }
  try {
    if (extension === "json") {
      return JSON.parse(text);
    }
    if (extension === "yaml" || extension === "yml") {
      return parseYaml(text);
    }
    if (extension === "toml") {
      return parseToml(text);
    }
    return null;
  } catch {
    return null;
  }
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function formatScalar(value: unknown): string {
  if (typeof value === "string") return JSON.stringify(value);
  if (typeof value === "number" || typeof value === "boolean") return String(value);
  if (value === null) return "null";
  if (value === undefined) return "undefined";
  return JSON.stringify(value);
}

interface StructuredNodeProps {
  nodeKey: string;
  value: unknown;
  depth: number;
}

function StructuredNode({ nodeKey, value, depth }: StructuredNodeProps) {
  const indent = { paddingLeft: `${depth * 12}px` };
  if (Array.isArray(value)) {
    const summary = `array(${value.length})`;
    return (
      <Collapsible defaultOpen>
        <div style={indent} className="text-xs">
          <CollapsibleTrigger className="flex items-center gap-1 group">
            <ChevronRight className="h-3 w-3 group-data-[state=open]:hidden text-muted-foreground" />
            <ChevronDown className="h-3 w-3 group-data-[state=closed]:hidden text-muted-foreground" />
            <span className="font-medium text-indigo-700 dark:text-indigo-300">{nodeKey}</span>
            <span className="text-muted-foreground">: {summary}</span>
          </CollapsibleTrigger>
        </div>
        <CollapsibleContent className="space-y-1">
          {value.map((item, index) => {
            if (isRecord(item) || Array.isArray(item)) {
              return (
                <StructuredNode
                  key={`${nodeKey}-${index}`}
                  nodeKey={`- [${index}]`}
                  value={item}
                  depth={depth + 1}
                />
              );
            }
            return (
              <div
                key={`${nodeKey}-${index}`}
                style={{ paddingLeft: `${(depth + 1) * 12}px` }}
                className="text-xs"
              >
                <span className="text-indigo-700 dark:text-indigo-300">-</span>{" "}
                <span className="text-foreground/90">{formatScalar(item)}</span>
              </div>
            );
          })}
        </CollapsibleContent>
      </Collapsible>
    );
  }

  if (isRecord(value)) {
    const keysCount = Object.keys(value).length;
    const summary = `map(${keysCount})`;
    return (
      <Collapsible defaultOpen>
        <div style={indent} className="text-xs">
          <CollapsibleTrigger className="flex items-center gap-1 group">
            <ChevronRight className="h-3 w-3 group-data-[state=open]:hidden text-muted-foreground" />
            <ChevronDown className="h-3 w-3 group-data-[state=closed]:hidden text-muted-foreground" />
            <span className="font-medium text-indigo-700 dark:text-indigo-300">{nodeKey}</span>
            <span className="text-muted-foreground">: {summary}</span>
          </CollapsibleTrigger>
        </div>
        <CollapsibleContent className="space-y-1">
          {Object.entries(value).map(([key, childValue]) => (
            <StructuredNode
              key={`${nodeKey}-${key}`}
              nodeKey={key}
              value={childValue}
              depth={depth + 1}
            />
          ))}
        </CollapsibleContent>
      </Collapsible>
    );
  }

  return (
    <div style={indent} className="text-xs">
      <span className="font-medium text-indigo-700 dark:text-indigo-300">{nodeKey}</span>
      <span className="text-muted-foreground">: </span>
      <span className="text-foreground/90">{formatScalar(value)}</span>
    </div>
  );
}

interface StructuredArtifactPreviewProps {
  filepath: string;
  preview: NamedArtifactPreview | undefined;
  /** Larger scroll areas when shown in fullscreen dialog. */
  density?: "default" | "relaxed";
}

export function StructuredArtifactPreview({
  filepath,
  preview,
  density = "default",
}: StructuredArtifactPreviewProps) {
  if (!preview) {
    return <p className="text-xs text-muted-foreground">Loading preview...</p>;
  }

  const relaxed = density === "relaxed";
  const scrollMax = relaxed ? "" : "max-h-80 overflow-auto";
  const preMax = relaxed ? "" : "max-h-64 overflow-auto";
  const imgWrap = relaxed ? "max-h-[min(90vh,64rem)]" : "max-h-96";

  if (preview.status === "image_ok") {
    return (
      <div
        className={`flex max-w-full justify-center overflow-auto rounded border border-border bg-muted/30 p-2 ${imgWrap}`}
      >
        <img
          src={preview.dataUrl}
          alt=""
          className={`max-w-full object-contain ${relaxed ? "max-h-[min(90vh,64rem)]" : "max-h-96"}`}
        />
      </div>
    );
  }

  if (preview.status === "too_large") {
    return (
      <p className="text-xs text-amber-600">
        Can&apos;t preview: {preview.message}
      </p>
    );
  }

  if (preview.status === "binary") {
    return (
      <p className="text-xs text-amber-600">
        Can&apos;t preview: binary file is not displayed in UI.
      </p>
    );
  }

  if (preview.status === "decode_error") {
    return (
      <p className="text-xs text-amber-600">
        Can&apos;t preview: file is not valid UTF-8 text.
      </p>
    );
  }

  const structuredValue = tryParseStructured(filepath, preview.text);
  if (structuredValue !== null) {
    return (
      <div
        className={`rounded border border-border bg-background/80 p-2 ${scrollMax}`}
      >
        <StructuredNode nodeKey="root" value={structuredValue} depth={0} />
      </div>
    );
  }

  if (preview.status === "ok" && isMarkdownFilepath(filepath, preview.contentType)) {
    return (
      <div
        className={`rounded border border-border bg-background/80 p-3 ${scrollMax}`}
      >
        <MarkdownPreview markdown={preview.text} className="docs-prose text-sm" />
      </div>
    );
  }

  return (
    <pre
      className={`text-xs bg-background/80 border border-border p-2 rounded whitespace-pre-wrap ${preMax}`}
    >
      {preview.text}
    </pre>
  );
}

