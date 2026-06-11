import { create } from "zustand";
import { persist } from "zustand/middleware";

/** Per-project map of experiment id → persisted canvas position */
export type DagLayoutPositions = Record<string, { x: number; y: number }>;

/** Per-project map of experiment id → persisted card width (px). */
export type DagNodeSizes = Record<string, { width: number }>;

/** Stable fallback for selectors — inline `{}` breaks useSyncExternalStore snapshot caching (React 19). */
export const EMPTY_DAG_LAYOUT_POSITIONS: DagLayoutPositions = {};
export const EMPTY_DAG_NODE_SIZES: DagNodeSizes = {};

function layoutPositionsEqual(
  a: DagLayoutPositions,
  b: DagLayoutPositions
): boolean {
  const aKeys = Object.keys(a);
  const bKeys = Object.keys(b);
  if (aKeys.length !== bKeys.length) return false;
  const eps = 1e-4;
  for (const k of aKeys) {
    const pa = a[k];
    const pb = b[k];
    if (!pb) return false;
    if (Math.abs(pa.x - pb.x) > eps || Math.abs(pa.y - pb.y) > eps) return false;
  }
  return true;
}

interface DagLayoutStoreState {
  layoutsByProject: Record<string, DagLayoutPositions>;
  sizesByProject: Record<string, DagNodeSizes>;
  updateNodePosition: (
    projectId: string,
    experimentId: string,
    position: { x: number; y: number }
  ) => void;
  updateNodeSize: (
    projectId: string,
    experimentId: string,
    width: number
  ) => void;
  /** Replaces the whole project map so every visible node is persisted; drops removed experiment ids. */
  replaceProjectLayout: (
    projectId: string,
    positions: DagLayoutPositions
  ) => void;
  clearProjectLayout: (projectId: string) => void;
}

export const useDagLayoutStore = create<DagLayoutStoreState>()(
  persist(
    (set) => ({
      layoutsByProject: {},
      sizesByProject: {},
      updateNodePosition: (projectId, experimentId, position) =>
        set((state) => ({
          layoutsByProject: {
            ...state.layoutsByProject,
            [projectId]: {
              ...(state.layoutsByProject[projectId] ?? EMPTY_DAG_LAYOUT_POSITIONS),
              [experimentId]: position,
            },
          },
        })),
      updateNodeSize: (projectId, experimentId, width) =>
        set((state) => ({
          sizesByProject: {
            ...(state.sizesByProject ?? EMPTY_DAG_NODE_SIZES),
            [projectId]: {
              ...(state.sizesByProject?.[projectId] ?? EMPTY_DAG_NODE_SIZES),
              [experimentId]: { width },
            },
          },
        })),
      replaceProjectLayout: (projectId, positions) =>
        set((state) => {
          const prev = state.layoutsByProject[projectId] ?? EMPTY_DAG_LAYOUT_POSITIONS;
          if (layoutPositionsEqual(prev, positions)) {
            return state;
          }
          return {
            layoutsByProject: {
              ...state.layoutsByProject,
              [projectId]: positions,
            },
          };
        }),
      clearProjectLayout: (projectId) =>
        set((state) => {
          const nextLayouts = { ...state.layoutsByProject };
          const nextSizes = { ...(state.sizesByProject ?? EMPTY_DAG_NODE_SIZES) };
          delete nextLayouts[projectId];
          delete nextSizes[projectId];
          return { layoutsByProject: nextLayouts, sizesByProject: nextSizes };
        }),
    }),
    {
      name: "experiment-tracker-dag-layouts",
      partialize: (state) => ({
        layoutsByProject: state.layoutsByProject,
        sizesByProject: state.sizesByProject,
      }),
    }
  )
);
