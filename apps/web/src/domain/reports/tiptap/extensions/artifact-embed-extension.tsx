"use client";

import { mergeAttributes, Node } from "@tiptap/core";
import { NodeViewWrapper, ReactNodeViewRenderer } from "@tiptap/react";
import { ArtifactEmbedBlock } from "../embed-blocks/artifact-embed-block";
import { defaultArtifactEmbedAttrs, type ArtifactEmbedAttrs } from "../embed-blocks/types";

function normalizeArtifactAttrs(raw: Record<string, unknown>): ArtifactEmbedAttrs {
  const base = defaultArtifactEmbedAttrs();
  const ids = raw.experimentIds;
  const nameFilter = typeof raw.nameFilter === "string" ? raw.nameFilter : base.nameFilter;
  let step: number | null = base.step;
  if (raw.step === null || raw.step === undefined) {
    step = null;
  } else if (typeof raw.step === "number" && Number.isFinite(raw.step)) {
    step = raw.step;
  }
  return {
    experimentIds: Array.isArray(ids) ? ids.map(String) : base.experimentIds,
    nameFilter,
    step,
  };
}

export const ArtifactEmbedExtension = Node.create({
  name: "artifactEmbed",
  group: "block",
  atom: true,
  draggable: true,

  addAttributes() {
    return {
      experimentIds: { default: [] },
      nameFilter: { default: "" },
      step: { default: null },
    };
  },

  parseHTML() {
    return [{ tag: 'div[data-type="artifact-embed"]' }];
  },

  renderHTML({ HTMLAttributes }) {
    return ["div", mergeAttributes(HTMLAttributes, { "data-type": "artifact-embed" })];
  },

  addNodeView() {
    return ReactNodeViewRenderer((props) => {
      const attrs = normalizeArtifactAttrs(props.node.attrs as Record<string, unknown>);
      return (
        <NodeViewWrapper className="artifact-embed-node my-3">
          <ArtifactEmbedBlock
            attrs={attrs}
            selected={props.selected}
            onAttrsChange={(patch) => props.updateAttributes(patch)}
          />
        </NodeViewWrapper>
      );
    });
  },
});
