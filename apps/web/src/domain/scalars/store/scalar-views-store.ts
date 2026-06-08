import { parseISO } from "date-fns";
import { create } from "zustand";

import { createClientId } from "@/lib/utils";
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

function persistViews(viewsByProject: Record<string, ScalarSavedView[]>) {
  if (typeof window === "undefined") return;
  try {
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify(viewsByProject));
  } catch {
    /* ignore quota / private mode */
  }
}

function sortLatestFirst(views: ScalarSavedView[]): ScalarSavedView[] {
  return [...views].sort((a, b) => {
    return parseISO(b.updatedAt).getTime() - parseISO(a.updatedAt).getTime();
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
      id: createClientId(),
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
    const updated = currentProjectViews.map((view) =>
      view.id === viewId ? { ...view, name } : view
    );
    const nextViewsByProject = {
      ...get().viewsByProject,
      [projectId]: updated,
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
