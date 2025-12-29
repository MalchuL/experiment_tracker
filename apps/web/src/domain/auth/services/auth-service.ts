import { serviceClients } from "@/lib/api/clients/axios-client";
import { API_ROUTES } from "@/lib/constants/api-routes";
import { User } from "@/shared/types";

export interface LoginPayload {
    email: string;
    password: string;
}

export interface SignUpPayload {
    email: string;
    password: string;
    displayName?: string;
}

export interface AuthService {
    login: (payload: LoginPayload) => Promise<void>;
    register: (payload: SignUpPayload) => Promise<void>;
    updateUser: (user: User) => Promise<void>;
    getUser: () => Promise<User>;
    logout: () => void;
}

export const authService = {
    login: async (payload: LoginPayload) => {
        const response = await serviceClients.api.post(API_ROUTES.AUTH.LOGIN, payload);
        return response.data;
    },
    register: async (payload: SignUpPayload) => {
        const response = await serviceClients.api.post(API_ROUTES.AUTH.REGISTER, payload);
        return response.data;
    },
    updateUser: async (user: User) => {
        const response = await serviceClients.api.patch(API_ROUTES.USERS.ME, user);
        return response.data;
    },
    getUser: async () => {
        const response = await serviceClients.api.get(API_ROUTES.USERS.ME);
        return response.data;
    },
    logout: async () => {
        const response = await serviceClients.api.post(API_ROUTES.AUTH.LOGOUT);
        return response.data;
    },
}