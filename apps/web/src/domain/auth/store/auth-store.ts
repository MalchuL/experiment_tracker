import { create } from "zustand";
import { User } from "@/shared/types";
import { serviceClients } from "@/lib/api/clients/axios-client";
import { API_ROUTES } from "@/lib/constants/api-routes";
import { deleteAuthToken, getAuthToken, setAuthToken } from "../utils/token";


interface AuthStoreState {
    user: User | null;
    token: string | null;
    isLoading: boolean;
    isAuthenticated: boolean;
    setToken: (token: string | null) => void;
    setUser: (user: User | null) => void;
    setIsLoading: (isLoading: boolean) => void;
    setIsAuthenticated: (isAuthenticated: boolean) => void;
    logout: () => void;
}


export const useAuthStore = create<AuthStoreState>((set) => ({
  user: null,
  setUser: (user: User | null) => set({ user }),
  token: getAuthToken(),
  setToken: (token: string | null) => {
    set({ token });
    if (token) {
      setAuthToken(token);
      set({ isAuthenticated: true });
    } else {
      deleteAuthToken();
      set({ isAuthenticated: false });
    }
  },
  isLoading: true,
  setIsLoading: (isLoading: boolean) => set({ isLoading }),
  isAuthenticated: !!getAuthToken(),
  setIsAuthenticated: (isAuthenticated: boolean) => set({ isAuthenticated }),
  logout: () => {
    deleteAuthToken();
    set({ user: null, token: null, isAuthenticated: false });
  },
}));
