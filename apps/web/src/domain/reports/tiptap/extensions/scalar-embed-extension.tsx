"use client";

import { mergeAttributes, Node } from "@tiptap/core";
import { NodeViewWrapper, ReactNodeViewRenderer } from "@tiptap/react";
import { ScalarEmbedBlock } from "../embed-blocks/scalar-embed-block";
import { defaultScalarEmbedAttrs, type ScalarEmbedAttrs } from "../embed-blocks/types";

function normalizeScalarAttrs(raw: Record<string, unknown>): ScalarEmbedAttrs {
  const base = defaultScalarEmbedAttrs();
  const ids = raw.experimentIds;
  const keys = raw.scalarKeys;
  return {
    experimentIds: Array.isArray(ids) ? ids.map(String) : base.experimentIds,
    scalarKeys: Array.isArray(keys) ? keys.map(String) : base.scalarKeys,
  };
}

export const ScalarEmbedExtension = Node.create({
  name: "scalarEmbed",
  group: "block",
  atom: true,
  draggable: true,

  addAttributes() {
    return {
      experimentIds: { default: [] },
      scalarKeys: { default: [] },
    };
  },

  parseHTML() {
    return [{ tag: 'div[data-type="scalar-embed"]' }];
  },

  renderHTML({ HTMLAttributes }) {
    return ["div", mergeAttributes(HTMLAttributes, { "data-type": "scalar-embed" })];
  },

  addNodeView() {
    return ReactNodeViewRenderer((props) => {
      const attrs = normalizeScalarAttrs(props.node.attrs as Record<string, unknown>);
      return (
        <NodeViewWrapper className="scalar-embed-node my-3">
          <ScalarEmbedBlock
            attrs={attrs}
            selected={props.selected}
            onAttrsChange={(patch) => props.updateAttributes(patch)}
          />
        </NodeViewWrapper>
      );
    });
  },
});
