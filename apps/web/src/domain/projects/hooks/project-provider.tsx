import { createContext, useContext } from "react";
import { Project, UpdateProject } from "../types";
import { ProjectHookOptions, useProject } from "./project-hook";


export interface ProjectProviderType {
    project: Project | undefined;
    isLoading: boolean;
    updateIsPending: boolean;
    deleteIsPending: boolean;
    updateProject: (project: UpdateProject, options?: ProjectHookOptions) => Promise<void>;
    deleteProject: (options?: ProjectHookOptions) => Promise<void>;
}

const ProjectContext = createContext<ProjectProviderType | null>(null);


export function ProjectProvider({ children, projectId }: { children: React.ReactNode, projectId: string }) {
    const { project, isLoading, updateIsPending, deleteIsPending, updateProject, deleteProject } = useProject(projectId);

    const value: ProjectProviderType = {
        project,
        isLoading,
        updateIsPending,
        deleteIsPending,
        updateProject,
        deleteProject,
    };

    return (
        <ProjectContext.Provider value={value}>
            {children}
        </ProjectContext.Provider>
    );
}

export function useCurrentProject() {
    const context = useContext(ProjectContext);
    if (!context) {
        throw new Error("useCurrentProject must be used within a ProjectProvider");
    }
    return context;
}