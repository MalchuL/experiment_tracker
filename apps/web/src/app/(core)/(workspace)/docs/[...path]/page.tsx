import { notFound } from "next/navigation";
import { DocsPageShell } from "@/components/docs/docs-page-shell";
import { DocsMarkdown } from "@/components/docs/docs-markdown";
import { getDocManifestEntry, getStaticDocPathParams } from "@/lib/docs/docs-manifest";
import { loadDocMarkdown } from "@/lib/docs/load-doc";
import { extractDocToc } from "@/lib/docs/extract-doc-toc";

/** Single doc article: `content/docs/{path}.md` matched via `DOCS_MANIFEST`. */

type PageProps = {
  params: Promise<{ path: string[] }>;
};

export function generateStaticParams() {
  return getStaticDocPathParams();
}

export default async function DocCatchAllPage({ params }: PageProps) {
  const { path: segments } = await params;
  if (!segments?.length) {
    notFound();
  }

  const meta = getDocManifestEntry(segments);
  if (!meta) {
    notFound();
  }

  const markdown = await loadDocMarkdown(segments);
  if (markdown === null) {
    notFound();
  }

  const toc = extractDocToc(markdown);

  return (
    <DocsPageShell currentPath={meta.path} toc={toc}>
      <div className="max-w-3xl pb-12">
        <DocsMarkdown markdown={markdown} toc={toc} className="docs-prose" />
      </div>
    </DocsPageShell>
  );
}
