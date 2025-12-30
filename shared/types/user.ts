export interface User {
    id: string;
    email: string;
    display_name: string | null;
    avatar_url: string | null;
    is_active: boolean;
    is_superuser: boolean;
    is_verified: boolean;
}