import { serviceClients } from "@/lib/api/clients/axios-client";
import { API_ROUTES } from "@/lib/constants/api-routes";
import { User } from "@/shared/types";
import { setAuthToken } from "../utils/token";

export interface LoginPayload {
    email: string;
    password: string;
}

export interface SignUpPayload {
    email: string;
    password: string;
    display_name: string;
}

export interface LoginResponse {
    access_token: string;
}

export interface AuthService {
    login: (payload: LoginPayload) => Promise<LoginResponse>;
    register: (payload: SignUpPayload) => Promise<User>;
    updateUser: (user: User) => Promise<User>;
    getUser: () => Promise<User>;
    logout: () => void;
}

// Helper functions for token storage
function setCookie(name: string, value: string, days = 7) {
  if (typeof document === "undefined") return;
  const expires = new Date(Date.now() + days * 864e5).toUTCString();
  document.cookie = `${name}=${encodeURIComponent(
    value
  )}; expires=${expires}; path=/`;
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
        // After registration, user is returned but we still need to login to get token
        // For now, return the user. The caller should handle login separately if needed.
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
        try {
            await serviceClients.api.post(API_ROUTES.AUTH.LOGOUT);
        } finally {
            // Always clear the token even if logout fails
            if (typeof document !== "undefined") {
                document.cookie = 'auth_token=; Max-Age=0; path=/';
            }
            delete serviceClients.api.defaults.headers.common['Authorization'];
        }
    },
}