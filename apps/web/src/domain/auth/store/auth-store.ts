import { create } from "zustand";
import { User } from "@/shared/types";
import { serviceClients } from "@/lib/api/clients/axios-client";
import { API_ROUTES } from "@/lib/constants/api-routes";

// Utility functions for cookies
function setCookie(name: string, value: string, days = 7) {
  if (typeof document === "undefined") return;
  const expires = new Date(Date.now() + days * 864e5).toUTCString();
  document.cookie = `${name}=${encodeURIComponent(
    value
  )}; expires=${expires}; path=/`;
}

function getCookie(name: string): string | null {
  if (typeof document === "undefined") return null;
  return (
    document.cookie
      .split("; ")
      .find((row) => row.startsWith(name + "="))
      ?.split("=")[1] || null
  );
}

function deleteCookie(name: string) {
  if (typeof document === "undefined") return;
  document.cookie = `${name}=; Max-Age=0; path=/`;
}


interface LoginPayload {
    email: string;
    password: string;
}

interface SignUpPayload {
    email: string;
    password: string;
    displayName?: string;
}

interface AuthStoreState {
    user: User | null;
    token: string | null;
    isLoading: boolean;
    isAuthenticated: boolean;
    setUser: (user: User | null) => void;
    setIsLoading: (isLoading: boolean) => void;
    setIsAuthenticated: (isAuthenticated: boolean) => void;
    logout: () => void;
}


export const useAuthStore = create<AuthStoreState>((set) => ({
  user: null,
  setUser: (user: User | null) => set({ user }),
  token: typeof window !== "undefined"
    ? getCookie("auth_token")
    : null,
  isLoading: true,
  setIsLoading: (isLoading: boolean) => set({ isLoading }),
  isAuthenticated: false,
  setIsAuthenticated: (isAuthenticated: boolean) => set({ isAuthenticated }),
  logout: () => {
    if (typeof window !== "undefined") {
      deleteCookie("auth_token");
    }
    set({ user: null, token: null, isAuthenticated: false });
  },
}));
