const FINAL_ARTIFACT_PREFIX = "final/";

export function getFileExtension(filename: string): string {
  const base = filename.trim();
  const dotIndex = base.lastIndexOf(".");
  if (dotIndex <= 0 || dotIndex === base.length - 1) {
    return "";
  }
  return base.slice(dotIndex);
}

export function stripFileExtension(name: string): string {
  const extension = getFileExtension(name);
  if (!extension) {
    return name.trim();
  }
  return name.slice(0, -extension.length).trim();
}

function sanitizePathSegment(name: string): string {
  return name.trim().replace(/[/\\:]/g, "_").replace(/\s+/g, "_");
}

/** Build stored path under `final/` from display name and optional uploaded file extension. */
export function buildFinalArtifactFilepath(displayName: string, fileExtension = ""): string {
  const base = sanitizePathSegment(stripFileExtension(displayName));
  if (!base) {
    return FINAL_ARTIFACT_PREFIX;
  }
  const normalizedExtension = fileExtension
    ? fileExtension.startsWith(".")
      ? fileExtension
      : `.${fileExtension}`
    : "";
  if (
    normalizedExtension &&
    !base.toLowerCase().endsWith(normalizedExtension.toLowerCase())
  ) {
    return `${FINAL_ARTIFACT_PREFIX}${base}${normalizedExtension}`;
  }
  return `${FINAL_ARTIFACT_PREFIX}${base}`;
}

export function defaultDisplayNameFromFile(file: File): string {
  return stripFileExtension(file.name) || file.name;
}
