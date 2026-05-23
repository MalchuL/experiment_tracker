"use client";

import { useState, type CSSProperties } from "react";
import { Plus, X } from "lucide-react";
import { Badge, badgeVariants } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { cn } from "@/lib/utils";

type ExperimentTagsEditorProps = {
  tags: string[];
  disabled?: boolean;
  onChange: (tags: string[]) => void | Promise<void>;
};

function tagHue(tag: string): number {
  let hash = 0;
  for (let i = 0; i < tag.length; i += 1) {
    hash = (hash * 31 + tag.charCodeAt(i)) % 360;
  }
  return hash;
}

function tagStyle(tag: string): CSSProperties {
  const hue = tagHue(tag);
  return {
    backgroundColor: `hsl(${hue} 70% 94%)`,
    borderColor: `hsl(${hue} 60% 72%)`,
    color: `hsl(${hue} 58% 24%)`,
  };
}

export function ExperimentTagsEditor({ tags, disabled = false, onChange }: ExperimentTagsEditorProps) {
  const [editorOpen, setEditorOpen] = useState(false);
  const [draft, setDraft] = useState("");

  const addTag = async () => {
    const nextTag = draft.trim();
    if (!nextTag) {
      setEditorOpen(false);
      setDraft("");
      return;
    }
    const exists = tags.some((tag) => tag.toLowerCase() === nextTag.toLowerCase());
    if (!exists) {
      await onChange([...tags, nextTag]);
    }
    setDraft("");
    setEditorOpen(false);
  };

  const removeTag = async (tagToRemove: string) => {
    await onChange(tags.filter((tag) => tag !== tagToRemove));
  };

  return (
    <>
      {tags.map((tag) => (
        <Badge
          key={tag}
          variant="outline"
          className="group/tag max-w-full gap-1 overflow-hidden pr-1"
          style={tagStyle(tag)}
          title={tag}
        >
          <span className="min-w-0 truncate">{tag}</span>
          <button
            type="button"
            className="ml-0.5 flex h-4 w-4 shrink-0 items-center justify-center rounded-sm opacity-0 transition-opacity hover:bg-black/10 focus-visible:opacity-100 focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring group-hover/tag:opacity-100"
            onClick={() => void removeTag(tag)}
            disabled={disabled}
            aria-label={`Remove tag ${tag}`}
          >
            <X className="h-3 w-3" aria-hidden />
          </button>
        </Badge>
      ))}
      {editorOpen ? (
        <form
          className={cn(badgeVariants({ variant: "outline" }), "gap-1 px-2")}
          onSubmit={(e) => {
            e.preventDefault();
            void addTag();
          }}
        >
          <Input
            value={draft}
            onChange={(e) => setDraft(e.target.value)}
            onBlur={() => void addTag()}
            onKeyDown={(e) => {
              if (e.key === "Escape") {
                e.preventDefault();
                setDraft("");
                setEditorOpen(false);
              }
            }}
            disabled={disabled}
            autoFocus
            className="h-5 w-24 border-0 bg-transparent p-0 text-xs shadow-none focus-visible:ring-0"
            placeholder="Tag"
          />
        </form>
      ) : (
        <button
          type="button"
          className={cn(badgeVariants({ variant: "outline" }), "gap-1")}
          onClick={() => setEditorOpen(true)}
          disabled={disabled}
          aria-label="Add tag"
        >
          <Plus className="h-3 w-3" aria-hidden />
          Tag
        </button>
      )}
    </>
  );
}
