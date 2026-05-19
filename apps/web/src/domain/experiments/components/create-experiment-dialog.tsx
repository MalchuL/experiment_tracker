"use client";

import { useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import {
    Dialog,
    DialogContent,
    DialogDescription,
    DialogHeader,
    DialogTitle,
    DialogTrigger,
} from "@/components/ui/dialog";
import {
    Form,
    FormControl,
    FormField,
    FormItem,
    FormLabel,
    FormMessage,
} from "@/components/ui/form";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Button } from "@/components/ui/button";
import { Plus } from "lucide-react";
import { useCreateExperiment, useExperiments } from "../hooks";
import { insertExperimentSchema, EXPERIMENT_COLORS} from "../schemas"
import { InsertExperiment } from "../types";
import { experimentFormSchema } from "../schemas";
import { ExperimentForm } from "../types/form";
import { ColorList } from "@/components/shared/color-list";
import { generateRandomColor } from "@/lib/colors";
import { parseFeatureNodes, type FeatureNode } from "@/lib/features/feature-tree";
import { FeatureBulletEditor } from "@/components/shared/feature-bullet-editor";
import { FeatureEditorLabelWithHelp } from "@/components/shared/feature-editor-help";
import {
    Select,
    SelectContent,
    SelectItem,
    SelectTrigger,
    SelectValue,
} from "@/components/ui/select";

interface CreateExperimentDialogProps {
    projectId: string;
    projectName?: string;
    trigger?: React.ReactNode;
}

function convertFormToInsertExperiment(form: ExperimentForm, projectId: string, features: FeatureNode[]): InsertExperiment {
    const insertData: InsertExperiment = {
        projectId,
        name: form.name,
        description: form.description || undefined,
        status: form.status,
        parentExperimentId: form.parentExperimentId || undefined,
        features,
        color: form.color,
    };
    return insertExperimentSchema.parse(insertData);
}

export function CreateExperimentDialog({
    projectId,
    projectName,
    trigger,
}: CreateExperimentDialogProps) {
    const [isOpen, setIsOpen] = useState(false);
    const [featureDraft, setFeatureDraft] = useState<FeatureNode[]>([]);
    const [featureEditorKey, setFeatureEditorKey] = useState(0);
    const { createExperiment, isPending } = useCreateExperiment(projectId, {
        onSuccess: () => {
            setIsOpen(false);
            form.reset();
            form.setValue("color", generateRandomColor());
            setFeatureDraft([]);
            setFeatureEditorKey((key) => key + 1);
        },
    });
    const { experiments: projectExperiments, isLoading: projectExperimentsLoading } =
        useExperiments(projectId, {
            enabled: isOpen,
            paginationMode: "auto",
            includeFeatures: true,
        });

    const form = useForm<ExperimentForm>({
        resolver: zodResolver(experimentFormSchema as any),
        defaultValues: {
            name: "",
            description: "",
            status: "planned",
            parentExperimentId: null,
            featuresJson: "[]",
            color: generateRandomColor(),
        },
    });

    const onSubmit = (data: ExperimentForm) => {
        const insertData = convertFormToInsertExperiment(data, projectId, featureDraft);
        createExperiment(insertData);
    };

    const selectParentExperiment = (parentExperimentId: string) => {
        const parentId = parentExperimentId === "__none__" ? null : parentExperimentId;
        form.setValue("parentExperimentId", parentId);
        const parentExperiment = projectExperiments.find((experiment) => experiment.id === parentId);
        setFeatureDraft(parentExperiment ? parseFeatureNodes(parentExperiment.features) : []);
        setFeatureEditorKey((key) => key + 1);
    };

    return (
        <Dialog open={isOpen} onOpenChange={setIsOpen}>
            <DialogTrigger asChild>
                {!!trigger || (
                    <Button data-testid="button-create-experiment">
                        <Plus className="w-4 h-4 mr-2" />
                        New Experiment
                    </Button>
                )}
            </DialogTrigger>
            <DialogContent className="max-w-2xl">
                <DialogHeader>
                    <DialogTitle>Create Experiment</DialogTitle>
                    <DialogDescription>
                        Add a new experiment to "{projectName}".
                    </DialogDescription>
                </DialogHeader>
                <Form {...form}>
                    <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-4">
                        <FormField
                            control={form.control}
                            name="name"
                            render={({ field }) => (
                                <FormItem>
                                    <FormLabel>Name</FormLabel>
                                    <FormControl>
                                        <Input
                                            placeholder="exp_001_lr_sweep"
                                            data-testid="input-experiment-name"
                                            {...field}
                                        />
                                    </FormControl>
                                    <FormMessage />
                                </FormItem>
                            )}
                        />
                        <FormField
                            control={form.control}
                            name="description"
                            render={({ field }) => (
                                <FormItem>
                                    <FormLabel>Description</FormLabel>
                                    <FormControl>
                                        <Textarea
                                            placeholder="Experiment description..."
                                            className="resize-none"
                                            data-testid="input-experiment-description"
                                            {...field}
                                        />
                                    </FormControl>
                                    <FormMessage />
                                </FormItem>
                            )}
                        />
                        <FormField
                            control={form.control}
                            name="parentExperimentId"
                            render={({ field }) => (
                                <FormItem>
                                    <FormLabel>Parent experiment</FormLabel>
                                    <Select
                                        value={field.value ?? "__none__"}
                                        onValueChange={selectParentExperiment}
                                        disabled={projectExperimentsLoading}
                                    >
                                        <FormControl>
                                            <SelectTrigger>
                                                <SelectValue placeholder="No parent" />
                                            </SelectTrigger>
                                        </FormControl>
                                        <SelectContent>
                                            <SelectItem value="__none__">No parent</SelectItem>
                                            {projectExperiments.map((experiment) => (
                                                <SelectItem key={experiment.id} value={experiment.id}>
                                                    {experiment.name} ({experiment.id.slice(0, 7)})
                                                </SelectItem>
                                            ))}
                                        </SelectContent>
                                    </Select>
                                    <FormMessage />
                                </FormItem>
                            )}
                        />
                        <FormField
                            control={form.control}
                            name="color"
                            render={({ field }) => (
                                <FormItem>
                                    <FormLabel>Color</FormLabel>
                                    <ColorList currentColor={field.value} useColorPalette={true} onColorChange={field.onChange} colors={EXPERIMENT_COLORS} />
                                    <FormMessage />
                                </FormItem>
                            )}
                        />
                        <FormField
                            control={form.control}
                            name="featuresJson"
                            render={() => (
                                <FormItem>
                                    <FormLabel>
                                        <FeatureEditorLabelWithHelp label="Features" />
                                    </FormLabel>
                                    <FormControl>
                                        <FeatureBulletEditor
                                            key={featureEditorKey}
                                            features={featureDraft}
                                            onChange={setFeatureDraft}
                                            className="min-h-44 max-h-72 overflow-auto rounded border border-input bg-background px-3 py-2 text-sm focus-visible:outline-none [&_ul]:list-disc [&_ul]:pl-5 [&_li]:my-1 [&_p]:m-0"
                                        />
                                    </FormControl>
                                    <FormMessage />
                                </FormItem>
                            )}
                        />
                        <div className="flex justify-end gap-2">
                            <Button
                                type="button"
                                variant="outline"
                                onClick={() => setIsOpen(false)}
                            >
                                Cancel
                            </Button>
                            <Button
                                type="submit"
                                disabled={isPending}
                                data-testid="button-submit-experiment"
                            >
                                {isPending ? "Creating..." : "Create"}
                            </Button>
                        </div>
                    </form>
                </Form>
            </DialogContent>
        </Dialog>
    );
}
