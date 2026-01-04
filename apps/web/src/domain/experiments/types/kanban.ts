import { ExperimentStatusType } from "./types";
import { Clock, Play, CheckCircle2, XCircle, LucideIcon } from "lucide-react";

export interface KanbanColumn {
  id: ExperimentStatusType;
  title: string;
  icon: LucideIcon;
  className: string;
}

export const KANBAN_COLUMNS: KanbanColumn[] = [
  { id: "planned", title: "Planned", icon: Clock, className: "bg-muted/50" },
  { id: "running", title: "Running", icon: Play, className: "bg-blue-500/10" },
  { id: "complete", title: "Complete", icon: CheckCircle2, className: "bg-green-500/10" },
  { id: "failed", title: "Failed", icon: XCircle, className: "bg-red-500/10" },
];

