import type { LoggedObjectGroups } from "@/domain/scalars/types";
import { groupNamesByPrefix } from "@/domain/scalars/utils/group-by-prefix";

export const SCALARS_CONTENT_TAB_ID = "scalars";

export interface ScalarsContentTab {
  id: string;
  label: string;
}

export function humanizeArtifactType(objectType: string): string {
  return objectType
    .split("_")
    .map((part) => (part.length > 0 ? part[0]!.toUpperCase() + part.slice(1) : part))
    .join(" ");
}

export function buildScalarsContentTabs(params: {
  visibleMetricNames: string[];
  objectGroups: LoggedObjectGroups;
  hiddenArtifactIds: Set<string>;
}): ScalarsContentTab[] {
  const tabs: ScalarsContentTab[] = [];

  if (params.visibleMetricNames.length > 0) {
    tabs.push({ id: SCALARS_CONTENT_TAB_ID, label: "Scalars" });
  }

  Object.keys(params.objectGroups)
    .sort((a, b) => a.localeCompare(b))
    .forEach((objectType) => {
      const byName = params.objectGroups[objectType] ?? {};
      const hasVisible = Object.keys(byName).some((name) => {
        const selectionKey = `${objectType}:${name}`;
        return !params.hiddenArtifactIds.has(selectionKey);
      });
      if (hasVisible) {
        tabs.push({
          id: objectType,
          label: humanizeArtifactType(objectType),
        });
      }
    });

  return tabs;
}

export function partitionNamesByPrefixForTab(names: string[]) {
  return groupNamesByPrefix(names);
}

export function visibleArtifactNamesForType(
  objectGroups: LoggedObjectGroups,
  objectType: string,
  hiddenArtifactIds: Set<string>
): string[] {
  const byName = objectGroups[objectType] ?? {};
  return Object.keys(byName)
    .filter((name) => !hiddenArtifactIds.has(`${objectType}:${name}`))
    .sort((a, b) => a.localeCompare(b));
}
