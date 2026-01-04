"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover";
import {
  Command,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
  CommandList,
} from "@/components/ui/command";
import { Project, ProjectMetric } from "../../types";
import { Plus, Trash2, TrendingUp, TrendingDown } from "lucide-react";
import { useToast } from "@/lib/hooks/use-toast";

const COMMON_METRICS = [
  "accuracy",
  "loss",
  "val_accuracy",
  "val_loss",
  "train_loss",
  "train_accuracy",
  "precision",
  "recall",
  "f1_score",
  "auc",
  "mse",
  "mae",
  "rmse",
  "r2",
  "perplexity",
  "bleu",
  "rouge",
  "learning_rate",
  "epoch",
  "step",
];

interface MetricsManagementProps {
  project: Project;
  onAddMetric: (metric: ProjectMetric) => void;
  onRemoveMetric: (metricName: string) => void;
  onUpdateMetricDirection: (metricName: string, direction: "maximize" | "minimize") => void;
  isPending: boolean;
}

export function MetricsManagement({
  project,
  onAddMetric,
  onRemoveMetric,
  onUpdateMetricDirection,
  isPending,
}: MetricsManagementProps) {
  const [newMetricName, setNewMetricName] = useState("");
  const [newMetricDirection, setNewMetricDirection] = useState<"maximize" | "minimize">("maximize");
  const [metricPopoverOpen, setMetricPopoverOpen] = useState(false);
  const { toast } = useToast();

  const handleAddMetric = () => {
    if (!newMetricName.trim() || !project) return;
    const existingMetric = project.metrics.find(m => m.name === newMetricName.trim());
    if (existingMetric) {
      toast({
        title: "Metric already exists",
        description: `A metric named "${newMetricName}" already exists.`,
        variant: "destructive",
      });
      return;
    }

    const newMetric: ProjectMetric = {
      name: newMetricName.trim(),
      direction: newMetricDirection,
      aggregation: "best",
    };

    onAddMetric(newMetric);
    setNewMetricName("");
    setMetricPopoverOpen(false);
  };

  return (
    <div className="space-y-4">
      <div className="flex gap-2">
        <Popover open={metricPopoverOpen} onOpenChange={setMetricPopoverOpen}>
          <PopoverTrigger asChild>
            <div className="flex-1 relative">
              <Input
                placeholder="Type to search metrics (e.g., accuracy)"
                value={newMetricName}
                onChange={(e) => {
                  setNewMetricName(e.target.value);
                  if (e.target.value.length > 0) {
                    setMetricPopoverOpen(true);
                  }
                }}
                onFocus={() => {
                  if (newMetricName.length > 0 || COMMON_METRICS.length > 0) {
                    setMetricPopoverOpen(true);
                  }
                }}
                className="w-full"
                data-testid="input-new-metric"
              />
            </div>
          </PopoverTrigger>
          <PopoverContent className="p-0 w-[300px]" align="start" onOpenAutoFocus={(e) => e.preventDefault()}>
            <Command>
              <CommandInput 
                placeholder="Search metrics..." 
                value={newMetricName}
                onValueChange={setNewMetricName}
              />
              <CommandList>
                <CommandEmpty>
                  {newMetricName.trim() ? (
                    <div className="p-2 text-sm">
                      Press Enter or click Add to create "{newMetricName}"
                    </div>
                  ) : (
                    "Type to search or create a metric"
                  )}
                </CommandEmpty>
                <CommandGroup heading="Suggestions">
                  {COMMON_METRICS
                    .filter(m => 
                      m.toLowerCase().includes(newMetricName.toLowerCase()) &&
                      !project.metrics.some(pm => pm.name === m)
                    )
                    .slice(0, 8)
                    .map((metricName) => (
                      <CommandItem
                        key={metricName}
                        value={metricName}
                        onSelect={(value) => {
                          setNewMetricName(value);
                          setMetricPopoverOpen(false);
                        }}
                      >
                        {metricName}
                      </CommandItem>
                    ))}
                </CommandGroup>
              </CommandList>
            </Command>
          </PopoverContent>
        </Popover>
        <Select
          value={newMetricDirection}
          onValueChange={(v) => setNewMetricDirection(v as "maximize" | "minimize")}
        >
          <SelectTrigger className="w-[140px]" data-testid="select-metric-direction">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="maximize">Maximize</SelectItem>
            <SelectItem value="minimize">Minimize</SelectItem>
          </SelectContent>
        </Select>
        <Button 
          onClick={handleAddMetric} 
          disabled={!newMetricName.trim() || isPending} 
          data-testid="button-add-metric"
        >
          <Plus className="w-4 h-4" />
        </Button>
      </div>

      <div className="space-y-2">
        {project.metrics.length === 0 ? (
          <p className="text-sm text-muted-foreground py-4 text-center">
            No metrics configured. Add metrics to track experiment performance.
          </p>
        ) : (
          project.metrics.map((metric) => (
            <div
              key={metric.name}
              className="flex items-center justify-between gap-4 p-3 rounded-md border"
            >
              <div className="flex items-center gap-2">
                <Badge variant="secondary">{metric.name}</Badge>
                {metric.direction === "maximize" ? (
                  <TrendingUp className="w-4 h-4 text-green-500" />
                ) : (
                  <TrendingDown className="w-4 h-4 text-red-500" />
                )}
              </div>
              <div className="flex items-center gap-2">
                <Select
                  value={metric.direction}
                  onValueChange={(v) =>
                    onUpdateMetricDirection(metric.name, v as "maximize" | "minimize")
                  }
                  disabled={isPending}
                >
                  <SelectTrigger className="w-[120px]">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="maximize">Maximize</SelectItem>
                    <SelectItem value="minimize">Minimize</SelectItem>
                  </SelectContent>
                </Select>
                <Button
                  size="icon"
                  variant="ghost"
                  onClick={() => onRemoveMetric(metric.name)}
                  disabled={isPending}
                  data-testid={`button-remove-metric-${metric.name}`}
                >
                  <Trash2 className="w-4 h-4" />
                </Button>
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
}

