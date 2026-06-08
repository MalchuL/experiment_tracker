"use client";

import { File } from "lucide-react";
import { Card } from "@/components/ui/card";
import { ScrollArea } from "@/components/ui/scroll-area";
import { cn } from "@/lib/utils";
import { getLanguageFromExtension } from "../lib/file-tree";
import { SyntaxHighlightedCode } from "./syntax-highlighted-code";

interface FileViewerProps {
  path: string;
  content: string;
  extension?: string;
  className?: string;
}

export function FileViewer({ path, content, extension, className }: FileViewerProps) {
  const language = getLanguageFromExtension(extension ?? path.split(".").pop());
  const lines = content.split("\n");
  const fileName = path.split("/").pop() || path;

  return (
    <Card className={cn("flex h-full flex-col overflow-hidden rounded-none border-0", className)}>
      <div className="flex items-center gap-2 border-b bg-muted/30 px-4 py-3">
        <File className="h-4 w-4 text-muted-foreground" />
        <span className="min-w-0 truncate text-sm font-medium">{fileName}</span>
        <span className="ml-auto shrink-0 text-xs text-muted-foreground">
          {lines.length} lines
        </span>
      </div>

      <ScrollArea className="flex-1" data-language={language}>
        <div className="font-mono text-sm">
          {lines.map((line, index) => (
            <div key={index} className="flex transition-colors hover:bg-accent/30">
              <div className="sticky left-0 min-w-14 select-none border-r bg-muted/20 px-4 py-1 text-right text-muted-foreground/60">
                {index + 1}
              </div>
              <div className="flex-1 px-4 py-1">
                <pre>
                  <code>
                    <SyntaxHighlightedCode content={line || " "} language={language} />
                  </code>
                </pre>
              </div>
            </div>
          ))}
        </div>
      </ScrollArea>
    </Card>
  );
}
