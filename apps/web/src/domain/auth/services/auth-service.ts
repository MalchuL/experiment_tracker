import { serviceClients } from "@/lib/api/clients/axios-client";
import { API_ROUTES } from "@/lib/constants/api-routes";
import { User } from "@/shared/types";
import { LoginPayload, SignUpPayload, LoginResponse } from "../types";



export interface AuthService {
    login: (payload: LoginPayload) => Promise<LoginResponse>;
    register: (payload: SignUpPayload) => Promise<User>;
    updateUser: (payload: Partial<User>) => Promise<User>;
    getUser: () => Promise<User>;
    changePassword: (payload: {
        currentPassword: string;
        newPassword: string;
    }) => Promise<{ success: boolean }>;
    logout: () => void;
}


export const authService: AuthService = {
    login: async (payload: LoginPayload): Promise<LoginResponse> => {
        // FastAPI Users BearerTransport expects form data with 'username' and 'password' fields
        const formData = new URLSearchParams();
        formData.append('username', payload.email); // FastAPI Users uses 'username' field for email
        formData.append('password', payload.password);
        
        const response = await serviceClients.api.post<LoginResponse>(
            API_ROUTES.AUTH.LOGIN,
            formData.toString(),
            {
                headers: {
                    'Content-Type': 'application/x-www-form-urlencoded',
                },
            }
        );
        return response.data;
    },
    register: async (payload: SignUpPayload): Promise<User> => {
        const response = await serviceClients.api.post<User>(API_ROUTES.AUTH.REGISTER, payload);
        return response.data;
    },
    updateUser: async (payload: Partial<User>) => {
        const response = await serviceClients.api.patch<User>(API_ROUTES.USERS.ME, payload);
        return response.data;
    },
    getUser: async () => {
        const response = await serviceClients.api.get(API_ROUTES.USERS.ME);
        return response.data;
    },
    changePassword: async (payload: {
        currentPassword: string;
        newPassword: string;
    }): Promise<{ success: boolean }> => {
        const response = await serviceClients.api.post<{ success: boolean }>(
            API_ROUTES.USERS.CHANGE_PASSWORD,
            payload,
        );
        return response.data;
    },
    logout: async () => {
        await serviceClients.api.post(API_ROUTES.AUTH.LOGOUT);
    },
}