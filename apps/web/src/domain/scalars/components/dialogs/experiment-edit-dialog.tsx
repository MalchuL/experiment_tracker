"use client";

import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { ExperimentEditForm } from "@/components/shared/experiment-edit-form";
import type { Experiment, UpdateExperiment } from "@/domain/experiments/types";

export interface ExperimentEditDialogProps {
  editExperiment: Experiment | null;
  setEditExperiment: (experiment: Experiment | null) => void;
  isSavingExperiment: boolean;
  onSaveExperiment: (
    payload: { id: string; data: UpdateExperiment },
    onSuccess: () => void,
  ) => void;
}

export function ExperimentEditDialog({
  editExperiment,
  setEditExperiment,
  isSavingExperiment,
  onSaveExperiment,
}: ExperimentEditDialogProps) {
  return (
    <Dialog
      open={!!editExperiment}
      onOpenChange={(open) => !open && setEditExperiment(null)}
    >
      <DialogContent className="max-w-lg">
        <DialogHeader>
          <DialogTitle>Edit Experiment</DialogTitle>
        </DialogHeader>
        {editExperiment && (
          <ExperimentEditForm
            experiment={editExperiment}
            isSaving={isSavingExperiment}
            onSave={(data) => {
              onSaveExperiment(
                {
                  id: editExperiment.id,
                  data: {
                    name: data.name,
                    description: data.description,
                    color: data.color,
                  },
                },
                () => setEditExperiment(null),
              );
            }}
          />
        )}
      </DialogContent>
    </Dialog>
  );
}
