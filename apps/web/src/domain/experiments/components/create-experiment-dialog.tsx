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
import { useCreateExperiment } from "../hooks/create-experiment-hook";
import { insertExperimentSchema, EXPERIMENT_COLORS} from "../schemas"
import { InsertExperiment } from "../types";
import { useToast } from "@/lib/hooks/use-toast";
import { experimentFormSchema } from "../schemas/experiment-form";
import { ExperimentForm } from "../types/form";
import { ColorList } from "@/components/shared/color-list";

interface CreateExperimentDialogProps {
    projectId: string;
    projectName?: string;
    trigger?: React.ReactNode;
}

function convertFormToInsertExperiment(form: ExperimentForm, projectId: string, onParseError: (error: Error) => void): InsertExperiment | null {
    let features: Record<string, unknown> = {};
    try {
        features = JSON.parse(form.featuresJson);
    } catch (error) {
        onParseError(error as Error);
        return null;
    }

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
    const { toast } = useToast();
    const { createExperiment, isPending } = useCreateExperiment(projectId, {
        onSuccess: () => {
            setIsOpen(false);
            form.reset();
        },
    });

    const form = useForm<ExperimentForm>({
        resolver: zodResolver(experimentFormSchema as any),
        defaultValues: {
            name: "",
            description: "",
            status: "planned",
            parentExperimentId: null,
            featuresJson: "{}",
            color: EXPERIMENT_COLORS[0],
        },
    });

    const onSubmit = (data: ExperimentForm) => {
        const insertData = convertFormToInsertExperiment(data, projectId, (error) => {
            toast({
                title: "Invalid JSON",
                description: "Features must be valid JSON.",
                variant: "destructive",
            });
        });
        if (insertData) {
            createExperiment(insertData);
        }
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
            <DialogContent className="max-w-md">
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
                            render={({ field }) => (
                                <FormItem>
                                    <FormLabel>Features (JSON)</FormLabel>
                                    <FormControl>
                                        <Textarea
                                            placeholder='{"optimizer": "AdamW", "lr": 0.0001}'
                                            className="resize-none font-mono text-sm"
                                            data-testid="input-features"
                                            {...field}
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

