export interface LoginPayload {
    email: string;
    password: string;
}

export interface SignUpPayload {
    email: string;
    password: string;
    displayName: string;
}

export interface LoginResponse {
    access_token: string;
}