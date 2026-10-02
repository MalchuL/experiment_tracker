"use client";

import { ImagePreviewDialog } from "./artifacts/image-preview-dialog";
import {
  ScalarFullscreenDialog,
  type ScalarFullscreenDialogProps,
} from "./dialogs/scalar-fullscreen-dialog";
import {
  ArtifactFullscreenDialog,
  type ArtifactFullscreenDialogProps,
} from "./dialogs/artifact-fullscreen-dialog";
import {
  ExperimentEditDialog,
  type ExperimentEditDialogProps,
} from "./dialogs/experiment-edit-dialog";

export interface ScalarsDialogsProps {
  scalar: ScalarFullscreenDialogProps;
  artifact: Omit<
    ArtifactFullscreenDialogProps,
    "visibleExperiments" | "onImagePreview"
  >;
  image: {
    imagePreview: { src: string; title: string } | null;
    setImagePreview: (value: { src: string; title: string } | null) => void;
  };
  experiment: ExperimentEditDialogProps;
}

export function ScalarsDialogs({
  scalar,
  artifact,
  image,
  experiment,
}: ScalarsDialogsProps) {
  return (
    <>
      <ScalarFullscreenDialog {...scalar} />
      <ArtifactFullscreenDialog
        {...artifact}
        visibleExperiments={scalar.experiments.visibleExperiments}
        onImagePreview={image.setImagePreview}
      />
      <ImagePreviewDialog
        imagePreview={image.imagePreview}
        onOpenChange={(open) => !open && image.setImagePreview(null)}
      />
      <ExperimentEditDialog {...experiment} />
    </>
  );
}
