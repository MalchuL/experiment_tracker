import { API_ROUTES } from "@/lib/constants/api-routes";
import { serviceClients } from "@/lib/api/clients/axios-client";
import { useQuery } from "@tanstack/react-query";
import { User } from "@/shared/types";
import { useAuthStore } from "../store/auth-store";
import { authService, LoginPayload, SignUpPayload } from "../services/auth-service";
import { useMutation } from "@tanstack/react-query";
import { useCallback } from "react";

export interface AuthHookResult {
    user: User | null;
    isLoading: boolean;
    isAuthenticated: boolean;
    login(payload: LoginPayload, {onSuccess, onError}: {onSuccess: () => void, onError: (error: Error) => void}): Promise<void>;
    register(payload: SignUpPayload, {onSuccess, onError}: {onSuccess: () => void, onError: (error: Error) => void}): Promise<void>;
    updateUser(payload: User, {onSuccess, onError}: {onSuccess: () => void, onError: (error: Error) => void}): Promise<void>;
    logout({onSuccess, onError}: {onSuccess: () => void, onError: (error: Error) => void}): Promise<void>;
    error: Error | null;
}

export function useAuthService(): AuthHookResult {
    const { user, isLoading, isAuthenticated, setUser, setIsLoading, setIsAuthenticated } = useAuthStore();
    // User Query
    const {
        data,
        isLoading: queryLoading,
        error,
    } = useQuery({
        queryKey: ["auth", isAuthenticated],
        queryFn: async () => {
            // guard if not authenticated, skip the request
            if (!isAuthenticated) return null;
            const response = await serviceClients.api.get<User>(API_ROUTES.USERS.ME);
            setUser(response.data);
            return response.data;
        },
        enabled: isAuthenticated,
        staleTime: 1000 * 60 * 5,
        retry: 1,
    });

    // Login mutation
    const loginMutation = useMutation({
        mutationFn: async (payload: LoginPayload) => {
            const user = await authService.login(payload);
            setUser(user);
            setIsAuthenticated(true);
            return user;
        },
        onError: () => {
            setIsAuthenticated(false);
        }
    });

    // Register mutation
    const registerMutation = useMutation({
        mutationFn: async (payload: SignUpPayload) => {
            const user = await authService.register(payload);
            setUser(user);
            setIsAuthenticated(true);
            return user;
        },
        onError: () => {
            setIsAuthenticated(false);
        }
    });

    // Update user mutation
    const updateUserMutation = useMutation({
        mutationFn: async (payload: User) => {
            const user = await authService.updateUser(payload);
            setUser(user);
            return user;
        },
    });

    // Logout mutation
    const logoutMutation = useMutation({
        mutationFn: async () => {
            await authService.logout();
            setUser(null);
            setIsAuthenticated(false);
        },
        onError: () => {
            setIsAuthenticated(false);
        }
    });

    // Update local loading state based on query
    if (isLoading !== queryLoading) {
        setIsLoading(queryLoading);
    }
    const logout = useCallback(({onSuccess, onError}: {onSuccess: () => void, onError: (error: Error) => void}) => {
        return logoutMutation.mutateAsync(undefined, {
            onSuccess,
            onError,
        });  
    }, [logoutMutation]);

    return {
        user,
        isLoading,
        isAuthenticated,
        login: loginMutation.mutateAsync,
        register: registerMutation.mutateAsync,
        updateUser: updateUserMutation.mutateAsync,
        logout,
        error: error as Error | null,
    };

}   