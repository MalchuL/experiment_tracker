"use client";

import { useAuthService } from "../hooks/auth-hook";
import { useRouter } from "next/navigation";
import { FRONTEND_ROUTES } from "@/lib/constants/frontend-routes";
import { useEffect } from "react";

interface AuthGuardProps {
  children: React.ReactNode;
  requireAuth?: boolean;
}

export function AuthGuard({ children, requireAuth = true }: AuthGuardProps) {
  const { user, isLoading, isAuthenticated, login, register, updateUser, logout } = useAuthService();
  const router = useRouter();

  useEffect(() => {
    if (isLoading) return;
    if (requireAuth && !isAuthenticated) {
      router.push(FRONTEND_ROUTES.LOGIN);
    }
    if (!requireAuth && isAuthenticated) {
      router.push(FRONTEND_ROUTES.ROOT);
    }
  }, [isAuthenticated, requireAuth, isLoading]);

  if (isLoading) {
    return <div>Loading...</div>;
  }


  return children;
}
