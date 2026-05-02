"use client";

interface ArtifactMediaProps {
  objectType: string;
  src: string;
  name: string;
  experimentName: string;
  maxHeight: number;
  onImagePreview: (payload: { src: string; title: string }) => void;
  title: string;
}

export function ArtifactMedia({
  objectType,
  src,
  name,
  experimentName,
  maxHeight,
  onImagePreview,
  title,
}: ArtifactMediaProps) {
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
    return (
      <a href={src} target="_blank" rel="noreferrer" className="text-xs text-primary underline">
        Open logged text
      </a>
    );
  }
  return (
    <a href={src} target="_blank" rel="noreferrer" className="text-xs text-primary underline">
      Open logged object
    </a>
  );
}
