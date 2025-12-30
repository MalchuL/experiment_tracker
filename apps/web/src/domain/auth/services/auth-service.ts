import { serviceClients } from "@/lib/api/clients/axios-client";
import { API_ROUTES } from "@/lib/constants/api-routes";
import { User } from "@/shared/types";
import { LoginPayload, SignUpPayload, LoginResponse } from "../types/login";



export interface AuthService {
    login: (payload: LoginPayload) => Promise<LoginResponse>;
    register: (payload: SignUpPayload) => Promise<User>;
    updateUser: (user: User) => Promise<User>;
    getUser: () => Promise<User>;
    logout: () => void;
}


export const authService = {
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
    updateUser: async (user: User) => {
        const response = await serviceClients.api.patch(API_ROUTES.USERS.ME, user);
        return response.data;
    },
    getUser: async () => {
        const response = await serviceClients.api.get(API_ROUTES.USERS.ME);
        return response.data;
    },
    logout: async () => {
        await serviceClients.api.post(API_ROUTES.AUTH.LOGOUT);
    },
}