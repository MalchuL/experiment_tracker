"use client";

import { useCallback, useState } from "react";
import { Check, Copy } from "lucide-react";
import { useToast } from "@/lib/hooks/use-toast";
import { cn } from "@/lib/utils";

type EntityIdDisplayProps = {
  label: string;
  value: string;
  className?: string;
};

export function EntityIdDisplay({ label, value, className }: EntityIdDisplayProps) {
  const { toast } = useToast();
  const [copied, setCopied] = useState(false);

  const handleCopy = useCallback(async () => {
    try {
      await navigator.clipboard.writeText(value);
      setCopied(true);
      toast({ title: `${label} copied` });
      window.setTimeout(() => setCopied(false), 2000);
    } catch {
      toast({ title: `Failed to copy ${label.toLowerCase()}`, variant: "destructive" });
    }
  }, [label, toast, value]);

  return (
    <button
      type="button"
      onClick={handleCopy}
      className={cn(
        "group flex w-full items-center gap-2 rounded-md bg-muted/50 p-2 text-left text-xs font-mono text-muted-foreground transition-colors hover:bg-muted/70",
        className
      )}
      aria-label={`Copy ${label}`}
      data-testid="entity-id-display"
    >
      <span className="min-w-0 flex-1 truncate">
        {label}: {value}
      </span>
      {copied ? (
        <Check className="h-3.5 w-3.5 shrink-0" aria-hidden />
      ) : (
        <Copy
          className="h-3.5 w-3.5 shrink-0 opacity-60 transition-opacity group-hover:opacity-100"
          aria-hidden
        />
      )}
    </button>
  );
}
