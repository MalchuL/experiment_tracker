"use client";

import Link from "next/link";
import {
  NavigationMenu,
  NavigationMenuContent,
  NavigationMenuItem,
  NavigationMenuLink,
  NavigationMenuList,
  NavigationMenuTrigger,
  navigationMenuTriggerStyle,
} from "@/components/ui/navigation-menu";
import { cn } from "@/lib/utils";
import { FRONTEND_ROUTES } from "@/lib/constants/frontend-routes";
import { DocsTopicNavItems, useDocsTopicPath } from "@/components/docs/docs-topic-links";

export function WorkspaceDocsNav({ className }: { className?: string }) {
  const currentPath = useDocsTopicPath();

  return (
    <NavigationMenu viewport={false} className={cn("max-w-none justify-start", className)}>
      <NavigationMenuList className="flex-wrap gap-0">
        <NavigationMenuItem>
          <NavigationMenuTrigger data-testid="nav-docs-trigger">Documentation</NavigationMenuTrigger>
          <NavigationMenuContent>
            <ul className="grid min-w-[248px] gap-0.5 p-1.5">
              <li>
                <NavigationMenuLink asChild>
                  <Link href={FRONTEND_ROUTES.DOCS} className="font-medium" data-testid="nav-docs-all">
                    All docs
                  </Link>
                </NavigationMenuLink>
              </li>
              <DocsTopicNavItems currentPath={currentPath} variant="menu" testIdPrefix="nav-docs" />
            </ul>
          </NavigationMenuContent>
        </NavigationMenuItem>
        <NavigationMenuItem>
          <NavigationMenuLink asChild>
            <Link
              href={FRONTEND_ROUTES.PROJECTS}
              className={navigationMenuTriggerStyle()}
              data-testid="nav-menu-projects"
            >
              Projects
            </Link>
          </NavigationMenuLink>
        </NavigationMenuItem>
      </NavigationMenuList>
    </NavigationMenu>
  );
}
