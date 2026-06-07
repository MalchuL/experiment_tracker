"use client";

import { ScrollArea } from "@/components/ui/scroll-area";
import { cn } from "@/lib/utils";
import { getLanguageFromExtension } from "../lib/file-tree";
import { SyntaxHighlightedCode } from "./syntax-highlighted-code";

interface CodeViewerProps {
  fileName: string;
  content: string;
  className?: string;
}

export function CodeViewer({ fileName, content, className }: CodeViewerProps) {
  const lines = content.split("\n");
  const language = getLanguageFromExtension(fileName.split(".").pop());

  return (
    <div className={cn("flex h-full flex-col", className)}>
      <div className="border-b bg-muted/30 px-4 py-2 text-sm font-medium">
        {fileName}
      </div>
      <ScrollArea className="h-full w-full">
        <div className="min-w-max">
          <pre className="p-4 font-mono text-sm">
            {lines.map((line, index) => (
              <div key={index} className="flex gap-4">
                <span className="w-8 shrink-0 select-none text-right text-muted-foreground/60">
                  {index + 1}
                </span>
                <code className="flex-1 text-foreground/90">
                  <SyntaxHighlightedCode content={line || " "} language={language} />
                </code>
              </div>
            ))}
          </pre>
        </div>
      </ScrollArea>
    </div>
  );
}
