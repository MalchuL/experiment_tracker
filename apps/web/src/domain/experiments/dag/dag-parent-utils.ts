import type { Experiment } from "../types";

/** True if setting child's parent to `newParentId` would create a cycle. */
export function wouldCreateCycle(
  experiments: Experiment[],
  childId: string,
  newParentId: string
): boolean {
  const byId = new Map(experiments.map((e) => [e.id, e]));
  let cur: string | null = newParentId;
  const seen = new Set<string>();
  while (cur) {
    if (cur === childId) return true;
    if (seen.has(cur)) break;
    seen.add(cur);
    cur = byId.get(cur)?.parentExperimentId ?? null;
  }
  return false;
}

/** All experiment ids in the subtree rooted at `rootId` (children only, not root). */
export function getDescendantIds(experiments: Experiment[], rootId: string): Set<string> {
  const childrenByParent = new Map<string, string[]>();
  for (const e of experiments) {
    if (e.parentExperimentId) {
      const list = childrenByParent.get(e.parentExperimentId) ?? [];
      list.push(e.id);
      childrenByParent.set(e.parentExperimentId, list);
    }
  }
  const out = new Set<string>();
  const stack = [...(childrenByParent.get(rootId) ?? [])];
  while (stack.length) {
    const id = stack.pop()!;
    if (out.has(id)) continue;
    out.add(id);
    for (const c of childrenByParent.get(id) ?? []) {
      stack.push(c);
    }
  }
  return out;
}
