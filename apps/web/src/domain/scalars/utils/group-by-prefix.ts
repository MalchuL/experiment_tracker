export interface PrefixGroupedNames {
  ungrouped: string[];
  groups: { key: string; items: string[] }[];
}

export function splitPrefixGroup(name: string): { group: string | null; leaf: string } {
  const slashIndex = name.indexOf("/");
  if (slashIndex === -1) {
    return { group: null, leaf: name };
  }
  return {
    group: name.slice(0, slashIndex),
    leaf: name.slice(slashIndex + 1),
  };
}

export function groupNamesByPrefix(names: string[]): PrefixGroupedNames {
  const ungrouped: string[] = [];
  const byGroup = new Map<string, string[]>();

  for (const name of names) {
    const { group } = splitPrefixGroup(name);
    if (group === null) {
      ungrouped.push(name);
      continue;
    }
    const bucket = byGroup.get(group) ?? [];
    bucket.push(name);
    byGroup.set(group, bucket);
  }

  const groups = Array.from(byGroup.entries())
    .sort(([a], [b]) => a.localeCompare(b))
    .map(([key, items]) => ({
      key,
      items: [...items].sort((a, b) => a.localeCompare(b)),
    }));

  return { ungrouped, groups };
}
