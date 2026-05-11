"use client";

import { mergeAttributes, Node } from "@tiptap/core";
import { NodeViewWrapper, ReactNodeViewRenderer } from "@tiptap/react";
import { MetricEmbedBlock } from "../embed-blocks/metric-embed-block";
import { defaultMetricEmbedAttrs, type MetricEmbedAttrs } from "../embed-blocks/types";

function normalizeMetricAttrs(raw: Record<string, unknown>): MetricEmbedAttrs {
  const base = defaultMetricEmbedAttrs();
  const ids = raw.experimentIds;
  const names = raw.metricNames;
  return {
    experimentIds: Array.isArray(ids) ? ids.map(String) : base.experimentIds,
    metricNames: Array.isArray(names) ? names.map(String) : base.metricNames,
  };
}

export const MetricEmbedExtension = Node.create({
  name: "metricEmbed",
  group: "block",
  atom: true,
  draggable: true,

  addAttributes() {
    return {
      experimentIds: { default: [] },
      metricNames: { default: [] },
    };
  },

  parseHTML() {
    return [{ tag: 'div[data-type="metric-embed"]' }];
  },

  renderHTML({ HTMLAttributes }) {
    return ["div", mergeAttributes(HTMLAttributes, { "data-type": "metric-embed" })];
  },

  addNodeView() {
    return ReactNodeViewRenderer((props) => {
      const attrs = normalizeMetricAttrs(props.node.attrs as Record<string, unknown>);
      return (
        <NodeViewWrapper className="metric-embed-node my-3">
          <MetricEmbedBlock
            attrs={attrs}
            selected={props.selected}
            onAttrsChange={(patch) => props.updateAttributes(patch)}
          />
        </NodeViewWrapper>
      );
    });
  },
});
