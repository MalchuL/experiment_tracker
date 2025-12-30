import { API_ROUTES } from "@/lib/constants/api-routes";
import { serviceClients } from "@/lib/api/clients/axios-client";
import { useQuery } from "@tanstack/react-query";
import { User } from "@/shared/types";
import { useAuthStore } from "../store/auth-store";
import { authService, LoginPayload, SignUpPayload } from "../services/auth-service";
import { useMutation } from "@tanstack/react-query";
import { useCallback, useEffect, useState } from "react";
import { getAuthToken } from "../utils/token";

export interface AuthHookResult {
    user: User | null;
    isLoading: boolean;
    isAuthenticated: boolean;
    login(payload: LoginPayload, {onSuccess, onError}?: {onSuccess?: () => void, onError?: (error: Error) => void}): Promise<void>;
    register(payload: SignUpPayload, {onSuccess, onError}?: {onSuccess?: () => void, onError?: (error: Error) => void}): Promise<void>;
    updateUser(payload: User, {onSuccess, onError}?: {onSuccess?: () => void, onError?: (error: Error) => void}): Promise<void>;
    logout({onSuccess, onError}?: {onSuccess?: () => void, onError?: (error: Error) => void}): Promise<void>;
    error: Error | null;
}

export function useAuthService(): AuthHookResult {
    const { user, isLoading, isAuthenticated, setUser, setIsLoading, setIsAuthenticated } = useAuthStore();
    const cookieToken = getAuthToken()
    useEffect(() => {
        if (cookieToken) {
            setIsAuthenticated(true);
        }
    }, [cookieToken]);
    // User Query
    const {
        isLoading: queryIsLoading,
        error,
    } = useQuery({
        queryKey: ["auth", cookieToken],
        queryFn: async () => {
            // guard if not cookie token, skip the request
            if (!cookieToken) return null;
            const data = await authService.getUser();
            setUser(data);
            return data;
        },
        enabled: !!cookieToken,
        staleTime: 1000 * 60 * 5,
        retry: 1,
    });
    // Login mutation
    const loginMutation = useMutation({
        mutationFn: async (payload: LoginPayload) => {
            const user = await authService.login(payload);
            setUser(user);
            setIsAuthenticated(true);
        },
        onError: () => {
            setIsAuthenticated(false);
        }
    });

    // Register mutation
    const registerMutation = useMutation({
        mutationFn: async (payload: SignUpPayload) => {
            console.log(payload);
            const user = await authService.register(payload);
            setUser(user);
            setIsAuthenticated(true);
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