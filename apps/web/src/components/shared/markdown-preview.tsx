"use client";

import type { ReactNode } from "react";
import Link from "next/link";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import rehypeSanitize from "rehype-sanitize";
import { docsRehypeSanitizeSchema } from "@/lib/docs/docs-sanitize-schema";

type MarkdownPreviewProps = {
  markdown: string;
  className?: string;
};

/**
 * Light GFM markdown renderer for user-uploaded content (artifacts, etc.).
 * No doc-specific directives, callouts, or TOC plugins.
 */
export function MarkdownPreview({ markdown, className }: MarkdownPreviewProps) {
  return (
    <div className={className}>
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        rehypePlugins={[[rehypeSanitize, docsRehypeSanitizeSchema]]}
        components={{
          a: ({ href, children }): ReactNode => {
            if (href?.startsWith("/")) {
              return <Link href={href}>{children as never}</Link>;
            }
            return (
              <a href={href} target="_blank" rel="noopener noreferrer">
                {children as never}
              </a>
            );
          },
          img: ({ src, alt }): ReactNode => {
            if (!src || typeof src !== "string") return null;
            return (
              <span className="docs-figure block my-4">
                {/* eslint-disable-next-line @next/next/no-img-element -- markdown URLs are dynamic */}
                <img
                  src={src}
                  alt={alt ?? ""}
                  loading="lazy"
                  decoding="async"
                  className="max-w-full h-auto rounded-md border border-border bg-muted/20"
                />
              </span>
            );
          },
        }}
      >
        {markdown}
      </ReactMarkdown>
    </div>
  );
}

export function isMarkdownFilepath(filepath: string, contentType?: string): boolean {
  const extension = filepath.split(".").pop()?.toLowerCase() ?? "";
  if (extension === "md" || extension === "markdown") return true;
  return contentType?.toLowerCase().includes("markdown") ?? false;
}
