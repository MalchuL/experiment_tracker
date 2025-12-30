import { useQuery } from "@tanstack/react-query";
import { User } from "@/shared/types";
import { useAuthStore } from "../store/auth-store";
import { authService } from "../services/auth-service";
import { LoginPayload, SignUpPayload } from "../types";
import { useMutation } from "@tanstack/react-query";
import { useCallback, useEffect } from "react";

interface AuthHookOptions {
    onSuccess?: () => void;
    onError?: (error: Error) => void;
}

export interface AuthHookResult {
    user: User | null;
    isLoading: boolean;
    isAuthenticated: boolean;
    login(payload: LoginPayload, options?: AuthHookOptions): Promise<void>;
    register(payload: SignUpPayload, options?: AuthHookOptions): Promise<void>;
    updateUser(payload: User, options?: AuthHookOptions): Promise<void>;
    logout(options?: AuthHookOptions): Promise<void>;
    error: Error | null;
}

export function useAuthService(): AuthHookResult {
    const { user, isLoading, token, setToken, isAuthenticated, setUser, setIsLoading, setIsAuthenticated } = useAuthStore();
    // User Query
    const {
        isLoading: queryIsLoading,
        error,
    } = useQuery({
        queryKey: ["auth", token],
        queryFn: async () => {
            // guard if not user, skip the request
            const data = await authService.getUser();
            setUser(data);
            return data;
        },
        enabled: user === null && !!token && !isLoading,
        staleTime: 1000 * 60 * 5,
        retry: 1,
    });
    // Login mutation
    const loginMutation = useMutation({
        mutationFn: async (payload: LoginPayload) => {
            const response = await authService.login(payload);
            setToken(response.access_token);
            setIsAuthenticated(true);
        },
        onError: () => {
            setIsAuthenticated(false);
        }
    });

    // Register mutation
    const registerMutation = useMutation({
        mutationFn: async (payload: SignUpPayload) => {
            await authService.register(payload);
            setToken(null);
        },
        onError: () => {
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
            setToken(null);
            setIsAuthenticated(false);
        },
    });

    // Update local loading state based on query
    useEffect(() => {
        if (isLoading !== queryIsLoading) {
            setIsLoading(queryIsLoading);
        }
    }, [isLoading, queryIsLoading]);
    
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