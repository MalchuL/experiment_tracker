import { create } from "zustand";
import type { ScalarSavedView } from "../types";

const STORAGE_KEY = "scalars:saved-views:v1";

interface ScalarViewsStoreState {
  viewsByProject: Record<string, ScalarSavedView[]>;
  hydrated: boolean;
  hydrate: () => void;
  saveView: (projectId: string, query: string, name: string) => ScalarSavedView;
  renameView: (projectId: string, viewId: string, name: string) => void;
  deleteView: (projectId: string, viewId: string) => void;
}

function createViewId(): string {
  if (typeof crypto !== "undefined" && "randomUUID" in crypto) {
    return crypto.randomUUID();
  }
  return `view-${Date.now()}-${Math.floor(Math.random() * 100000)}`;
}

function persistViews(viewsByProject: Record<string, ScalarSavedView[]>) {
  if (typeof window === "undefined") return;
  window.localStorage.setItem(STORAGE_KEY, JSON.stringify(viewsByProject));
}

function sortLatestFirst(views: ScalarSavedView[]): ScalarSavedView[] {
  return [...views].sort((a, b) => {
    return new Date(b.updatedAt).getTime() - new Date(a.updatedAt).getTime();
  });
}

export const useScalarViewsStore = create<ScalarViewsStoreState>((set, get) => ({
  viewsByProject: {},
  hydrated: false,

  hydrate: () => {
    if (typeof window === "undefined") return;
    if (get().hydrated) return;
    const raw = window.localStorage.getItem(STORAGE_KEY);
    if (!raw) {
      set({ hydrated: true });
      return;
    }
    try {
      const parsed = JSON.parse(raw) as Record<string, ScalarSavedView[]>;
      const normalized: Record<string, ScalarSavedView[]> = {};
      Object.entries(parsed).forEach(([projectId, views]) => {
        normalized[projectId] = sortLatestFirst(views ?? []);
      });
      set({ viewsByProject: normalized, hydrated: true });
    } catch {
      set({ viewsByProject: {}, hydrated: true });
    }
  },

  saveView: (projectId: string, query: string, name: string) => {
    const now = new Date().toISOString();
    const nextView: ScalarSavedView = {
      id: createViewId(),
      projectId,
      name,
      query,
      createdAt: now,
      updatedAt: now,
    };
    const currentProjectViews = get().viewsByProject[projectId] ?? [];
    const nextViewsByProject = {
      ...get().viewsByProject,
      [projectId]: [nextView, ...currentProjectViews],
    };
    persistViews(nextViewsByProject);
    set({ viewsByProject: nextViewsByProject });
    return nextView;
  },

  renameView: (projectId: string, viewId: string, name: string) => {
    const currentProjectViews = get().viewsByProject[projectId] ?? [];
    const now = new Date().toISOString();
    const updated = currentProjectViews.map((view) =>
      view.id === viewId ? { ...view, name, updatedAt: now } : view
    );
    const sorted = sortLatestFirst(updated);
    const nextViewsByProject = {
      ...get().viewsByProject,
      [projectId]: sorted,
    };
    persistViews(nextViewsByProject);
    set({ viewsByProject: nextViewsByProject });
  },

  deleteView: (projectId: string, viewId: string) => {
    const currentProjectViews = get().viewsByProject[projectId] ?? [];
    const filtered = currentProjectViews.filter((view) => view.id !== viewId);
    const nextViewsByProject = {
      ...get().viewsByProject,
      [projectId]: filtered,
    };
    persistViews(nextViewsByProject);
    set({ viewsByProject: nextViewsByProject });
  },
}));
