import { DocsPageShell } from "@/components/docs/docs-page-shell";
import { DocsIndexList } from "@/components/docs/docs-index-list";
import { DOCS_MANIFEST } from "@/lib/docs/docs-manifest";

/** `/docs` landing page: card grid of every `DOCS_MANIFEST` entry. */

export default function DocsIndexPage() {
  return (
    <DocsPageShell
      title="Documentation"
      description="Product and architecture notes for using ResearchTrack in the browser and with the wider platform."
      currentPath={null}
      toc={[]}
    >
      <div className="pb-10">
        <DocsIndexList entries={DOCS_MANIFEST} />
      </div>
    </DocsPageShell>
  );
}
