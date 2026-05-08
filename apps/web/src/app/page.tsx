"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { FRONTEND_ROUTES } from "@/lib/constants/frontend-routes";
import { useAuth } from "@/domain/auth/hooks/provider";
import { Skeleton } from "@/components/ui/skeleton";

export default function Home() {
  const router = useRouter();
  const { isLoading, isAuthenticated } = useAuth();

  useEffect(() => {
    if (isLoading) return;
    router.replace(isAuthenticated ? FRONTEND_ROUTES.PROJECTS : FRONTEND_ROUTES.LOGIN);
  }, [isLoading, isAuthenticated, router]);

  return <Skeleton className="h-screen w-full" />;
}
