import { cn } from "@/lib/utils";
import { SyntaxHighlightedCode } from "./syntax-highlighted-code";

type InlineDiffSide = "old" | "new";

interface InlineDiffTextProps {
  content?: string;
  compareWith?: string;
  side: InlineDiffSide;
  language?: string;
  className?: string;
}

type InlineSegment = {
  content: string;
  changed: boolean;
};

export function InlineDiffText({
  content = "",
  compareWith,
  side,
  language,
  className,
}: InlineDiffTextProps) {
  const segments =
    compareWith === undefined || content === compareWith
      ? [{ content: content || " ", changed: false }]
      : computeInlineSegments(content, compareWith);

  return (
    <code className={cn("whitespace-pre-wrap break-words", className)}>
      {segments.map((segment, index) => (
        <span
          key={`${index}-${segment.content}`}
          className={cn(
            segment.changed &&
              (side === "old"
                ? "rounded-sm bg-red-500/25 text-red-950 dark:text-red-100"
                : "rounded-sm bg-green-500/25 text-green-950 dark:text-green-100")
          )}
        >
          {segment.changed ? (
            segment.content || " "
          ) : (
            <SyntaxHighlightedCode content={segment.content || " "} language={language} />
          )}
        </span>
      ))}
    </code>
  );
}

function computeInlineSegments(content: string, compareWith: string): InlineSegment[] {
  let prefixLength = 0;
  const maxPrefixLength = Math.min(content.length, compareWith.length);

  while (
    prefixLength < maxPrefixLength &&
    content[prefixLength] === compareWith[prefixLength]
  ) {
    prefixLength += 1;
  }

  let suffixLength = 0;
  const maxSuffixLength = maxPrefixLength - prefixLength;

  while (
    suffixLength < maxSuffixLength &&
    content[content.length - 1 - suffixLength] ===
      compareWith[compareWith.length - 1 - suffixLength]
  ) {
    suffixLength += 1;
  }

  const prefix = content.slice(0, prefixLength);
  const changed =
    suffixLength > 0 ? content.slice(prefixLength, -suffixLength) : content.slice(prefixLength);
  const suffix = suffixLength > 0 ? content.slice(-suffixLength) : "";

  return [
    { content: prefix, changed: false },
    { content: changed || " ", changed: true },
    { content: suffix, changed: false },
  ].filter((segment) => segment.content.length > 0);
}
