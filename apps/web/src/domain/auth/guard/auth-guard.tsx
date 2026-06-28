"use client";

import { useAuthService } from "../hooks/auth-hook";
import { usePathname, useRouter } from "next/navigation";
import { FRONTEND_ROUTES, isPublicFrontendPath } from "@/lib/constants/frontend-routes";
import { useEffect } from "react";
import { Skeleton } from "@/components/ui/skeleton";

interface AuthGuardProps {
  children: React.ReactNode;
  requireAuth?: boolean;
}

export function AuthGuard({ children, requireAuth = true }: AuthGuardProps) {
  const { isLoading, isAuthenticated } = useAuthService();
  const router = useRouter();
  const pathname = usePathname();
  const isPublic = isPublicFrontendPath(pathname);

  useEffect(() => {
    if (isLoading) return;
    if (requireAuth && !isPublic && !isAuthenticated) {
      router.push(FRONTEND_ROUTES.LOGIN);
    }
    if (!requireAuth && isAuthenticated) {
      router.push(FRONTEND_ROUTES.PROJECTS);
    }
  }, [isAuthenticated, isLoading, isPublic, requireAuth, router]);

  if (isLoading) {
    return <Skeleton className="w-full h-full" />;
  }


  return children;
}
