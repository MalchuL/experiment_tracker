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