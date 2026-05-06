import { useEffect, useMemo } from "react";
import { faker } from "@faker-js/faker";
import { useScalarViewsStore } from "../store";
import type { ScalarSavedView } from "../types";

export function generateRandomViewName(): string {
  const adjective = faker.word.adjective();
  const animal = faker.animal.type();
  return `${titleCase(adjective)} ${titleCase(animal)}`;
}

function titleCase(value: string): string {
  return value
    .split(/[\s_-]+/)
    .filter(Boolean)
    .map((part) => `${part.charAt(0).toUpperCase()}${part.slice(1).toLowerCase()}`)
    .join(" ");
}

export interface UseScalarViewsResult {
  views: ScalarSavedView[];
  hydrated: boolean;
  saveCurrentView: (query: string, name?: string) => ScalarSavedView | null;
  renameView: (viewId: string, name: string) => void;
  deleteView: (viewId: string) => void;
}

export function useScalarViews(projectId?: string): UseScalarViewsResult {
  const {
    viewsByProject,
    hydrated,
    hydrate,
    saveView,
    renameView: renameStoreView,
    deleteView: deleteStoreView,
  } = useScalarViewsStore();

  useEffect(() => {
    hydrate();
  }, [hydrate]);

  const views = useMemo(() => {
    if (!projectId) return [];
    return viewsByProject[projectId] ?? [];
  }, [projectId, viewsByProject]);

  const saveCurrentView = (query: string, name?: string): ScalarSavedView | null => {
    if (!projectId) return null;
    const normalizedQuery = query.startsWith("?") ? query.slice(1) : query;
    return saveView(projectId, normalizedQuery, name?.trim() || generateRandomViewName());
  };

  const renameView = (viewId: string, name: string) => {
    if (!projectId) return;
    const nextName = name.trim();
    if (!nextName) return;
    renameStoreView(projectId, viewId, nextName);
  };

  const deleteView = (viewId: string) => {
    if (!projectId) return;
    deleteStoreView(projectId, viewId);
  };

  return {
    views,
    hydrated,
    saveCurrentView,
    renameView,
    deleteView,
  };
}
