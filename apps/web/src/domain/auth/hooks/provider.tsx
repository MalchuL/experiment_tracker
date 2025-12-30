"use client";

import { createContext, useContext, type ReactNode } from "react";
import { LoginPayload, SignUpPayload } from "../types";
import { useAuthService } from "./auth-hook";
import { User } from "@/shared/types";

interface AuthProviderOptions {
  onSuccess?: () => void;
  onError?: (error: Error) => void;
}

interface AuthContextType {
  user: User | null;
  isLoading: boolean;
  isAuthenticated: boolean;
  login: (payload: LoginPayload, options?: AuthProviderOptions) => Promise<void>;
  register: (payload: SignUpPayload, options?: AuthProviderOptions) => Promise<void>;
  updateUser: (payload: User, options?: AuthProviderOptions) => Promise<void>;
  logout: (options?: AuthProviderOptions) => Promise<void>;
}

const AuthContext = createContext<AuthContextType | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const { user, isLoading, isAuthenticated, login, register, updateUser, logout } = useAuthService();

  const value = {
    user,
    isLoading,
    isAuthenticated,
    login,
    register,
    updateUser,
    logout,
  };
  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
}
