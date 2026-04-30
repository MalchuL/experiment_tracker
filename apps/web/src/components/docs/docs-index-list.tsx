import Link from "next/link";
import { Card, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import type { DocManifestEntry } from "@/lib/docs/docs-manifest";
import { docIndexEntryPaddingStyle, docPathDepth } from "@/lib/docs/docs-manifest";
import { FRONTEND_ROUTES } from "@/lib/constants/frontend-routes";
import { cn } from "@/lib/utils";

type DocsIndexListProps = {
  entries: DocManifestEntry[];
};

/**
 * Grid of cards for `/docs`: each manifest entry links to its route; nesting depth tweaks card padding.
 */
export function DocsIndexList({ entries }: DocsIndexListProps) {
  const sorted = [...entries].sort((a, b) => a.path.localeCompare(b.path));

  return (
    <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
      {sorted.map((doc) => (
        <Link key={doc.path} href={FRONTEND_ROUTES.DOCS_DOC(doc.path)} className="block group">
          <Card
            className={cn(
              "h-full border-l-2 transition-colors hover:border-primary/40 hover:bg-muted/30",
              docPathDepth(doc.path) > 0 && "border-l-primary/30",
            )}
          >
            <CardHeader
              className="flex flex-col space-y-1.5 p-6"
              style={docIndexEntryPaddingStyle(doc.path)}
            >
              <CardTitle className="text-base group-hover:text-primary transition-colors">
                {doc.title}
              </CardTitle>
              <p className="text-xs font-mono text-muted-foreground truncate" title={doc.path}>
                {doc.path}
              </p>
              {doc.description ? (
                <CardDescription className="line-clamp-3">{doc.description}</CardDescription>
              ) : null}
            </CardHeader>
          </Card>
        </Link>
      ))}
    </div>
  );
}
