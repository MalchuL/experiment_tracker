"use client";

import { useMemo, useState } from "react";
import { BarChart3 } from "lucide-react";
import { EmptyState } from "@/components/shared/empty-state";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { CollapsiblePrefixGroup } from "./collapsible-prefix-group";
import {
  LoggedObjectsSection,
  type LoggedObjectsSectionProps,
} from "./logged-objects-section";
import {
  ScalarsPlotPanel,
  type ScalarsPlotPanelProps,
} from "./scalars-plot-panel";
import {
  buildScalarsContentTabs,
  partitionNamesByPrefixForTab,
  SCALARS_CONTENT_TAB_ID,
  visibleArtifactNamesForType,
} from "../utils/scalars-content-layout";

export interface ScalarsContentPanelProps extends ScalarsPlotPanelProps {
  artifacts: {
    data: Pick<
      LoggedObjectsSectionProps,
      "projectId" | "objectGroups" | "onImagePreview"
    > & { hiddenArtifactIds: Set<string> };
    steps: LoggedObjectsSectionProps["steps"];
    overrides: LoggedObjectsSectionProps["overrides"];
  };
}

export function ScalarsContentPanel({
  scalars,
  pagination,
  artifacts,
}: ScalarsContentPanelProps) {
  const { objectGroups, hiddenArtifactIds } = artifacts.data;
  const tabs = useMemo(
    () =>
      buildScalarsContentTabs({
        visibleMetricNames: scalars.metrics.visibleMetrics.map(
          (metric) => metric.name,
        ),
        objectGroups,
        hiddenArtifactIds,
      }),
    [scalars.metrics.visibleMetrics, objectGroups, hiddenArtifactIds],
  );
  const [activeTab, setActiveTab] = useState(
    () => tabs[0]?.id ?? SCALARS_CONTENT_TAB_ID,
  );
  const resolvedActiveTab = tabs.some((tab) => tab.id === activeTab)
    ? activeTab
    : (tabs[0]?.id ?? SCALARS_CONTENT_TAB_ID);
  const objects: LoggedObjectsSectionProps = {
    projectId: artifacts.data.projectId,
    objectGroups,
    visibleExperiments: scalars.experiments.visibleExperiments,
    size: scalars.size,
    steps: artifacts.steps,
    overrides: artifacts.overrides,
    onImagePreview: artifacts.data.onImagePreview,
    filter: { hiddenArtifactIds },
    showSectionHeader: false,
  };
  if (tabs.length === 0)
    return (
      <EmptyState
        icon={BarChart3}
        title="No scalars or logged objects"
        description="Select experiments with logged metrics or artifacts to view them here."
      />
    );
  return (
    <Tabs
      value={resolvedActiveTab}
      onValueChange={setActiveTab}
      className="space-y-3"
    >
      <TabsList className="h-auto flex-wrap justify-start">
        {tabs.map((tab) => (
          <TabsTrigger key={tab.id} value={tab.id}>
            {tab.label}
          </TabsTrigger>
        ))}
      </TabsList>
      {tabs.map((tab) => (
        <TabsContent
          key={tab.id}
          value={tab.id}
          forceMount
          className="space-y-4 data-[state=inactive]:hidden"
        >
          {tab.id === SCALARS_CONTENT_TAB_ID ? (
            resolvedActiveTab === SCALARS_CONTENT_TAB_ID && (
              <ScalarsPlotPanel scalars={scalars} pagination={pagination} />
            )
          ) : (
            <ArtifactTypePanel objects={objects} artifactType={tab.id} />
          )}
        </TabsContent>
      ))}
    </Tabs>
  );
}

function ArtifactTypePanel({
  objects,
  artifactType,
}: {
  objects: LoggedObjectsSectionProps;
  artifactType: string;
}) {
  const names = visibleArtifactNamesForType(
    objects.objectGroups,
    artifactType,
    objects.filter?.hiddenArtifactIds ?? new Set<string>(),
  );
  const partition = partitionNamesByPrefixForTab(names);
  const section = (artifactNames: string[]) => (
    <LoggedObjectsSection
      {...objects}
      filter={{ ...objects.filter, artifactType, artifactNames }}
    />
  );
  return (
    <>
      {partition.ungrouped.length > 0 && section(partition.ungrouped)}
      {partition.groups.map((group) => (
        <CollapsiblePrefixGroup
          key={group.key}
          title={group.key}
          count={group.items.length}
        >
          {section(group.items)}
        </CollapsiblePrefixGroup>
      ))}
    </>
  );
}
