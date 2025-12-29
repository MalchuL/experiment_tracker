"use client";

import { createContext, useContext, useState, useEffect, useCallback, type ReactNode } from "react";
import { LoginPayload, SignUpPayload } from "../services/auth-service";
import { useAuthService } from "../hooks/auth-hook";
import { User } from "@/shared/types";


interface AuthContextType {
  user: User | null;
  isLoading: boolean;
  isAuthenticated: boolean;
  login: (payload: LoginPayload, {onSuccess, onError}: {onSuccess?: () => void, onError?: (error: Error) => void}) => Promise<void>;
  register: (payload: SignUpPayload, {onSuccess, onError}?: {onSuccess?: () => void, onError?: (error: Error) => void}) => Promise<void>;
  updateUser: (payload: User, {onSuccess, onError}?: {onSuccess?: () => void, onError?: (error: Error) => void}) => Promise<void>;
  logout: ({onSuccess, onError}?: {onSuccess?: () => void, onError?: (error: Error) => void}) => Promise<void>;
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
