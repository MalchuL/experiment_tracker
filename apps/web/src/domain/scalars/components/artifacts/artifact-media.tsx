"use client";

import { useEffect, useState } from "react";
import {
  isPlotlyArtifactType,
  PlotlyArtifactMedia,
} from "@/domain/scalars/components/artifacts/plotly-artifact-media";

export interface ArtifactMediaProps {
  objectType: string;
  src: string;
  name: string;
  experimentName: string;
  maxHeight: number;
  onImagePreview: (payload: { src: string; title: string }) => void;
  title: string;
  metadata?: Record<string, string>;
}

export function ArtifactMedia({
  objectType,
  src,
  name,
  experimentName,
  maxHeight,
  onImagePreview,
  title,
  metadata,
}: ArtifactMediaProps) {
  const [textContent, setTextContent] = useState<string | null>(null);
  const [textError, setTextError] = useState<string | null>(null);

  useEffect(() => {
    if (objectType !== "text") {
      setTextContent(null);
      setTextError(null);
      return;
    }

    const controller = new AbortController();
    setTextError(null);

    void fetch(src, { signal: controller.signal })
      .then(async (response) => {
        if (!response.ok) {
          throw new Error(`Failed to load text (${response.status})`);
        }
        return response.text();
      })
      .then((content) => {
        setTextContent(content);
      })
      .catch((error: unknown) => {
        if (controller.signal.aborted) return;
        if (error instanceof Error) {
          setTextError(error.message);
          return;
        }
        setTextError("Failed to load text");
      });

    return () => {
      controller.abort();
    };
  }, [objectType, src]);

  if (objectType === "image") {
    return (
      <button type="button" className="flex w-full items-center justify-center" onClick={() => onImagePreview({ src, title })}>
        <img
          src={src}
          alt={`${name}-${experimentName}`}
          className="w-full rounded object-contain"
          style={{ maxHeight }}
        />
      </button>
    );
  }
  if (objectType === "video") {
    return <video src={src} controls className="w-full rounded" style={{ maxHeight }} />;
  }
  if (objectType === "audio") {
    return <audio src={src} controls className="w-full" />;
  }
  if (objectType === "text") {
    if (textError && !textContent) {
      return <p className="text-xs text-destructive">{textError}</p>;
    }
    return (
      <pre
        className="w-full overflow-auto whitespace-pre-wrap break-words rounded border bg-muted/30 p-2 text-xs"
        style={{ maxHeight }}
        aria-label={`Logged text for ${name}`}
      >
        {textContent ?? ""}
      </pre>
    );
  }
  if (isPlotlyArtifactType(objectType)) {
    return (
      <PlotlyArtifactMedia
        objectType={objectType}
        src={src}
        title={title}
        maxHeight={maxHeight}
        metadata={metadata}
      />
    );
  }
  return (
    <a href={src} target="_blank" rel="noreferrer" className="text-xs text-primary underline">
      Open logged object
    </a>
  );
}
