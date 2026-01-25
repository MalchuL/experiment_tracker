export interface User {
    id: string;
    email: string;
    displayName: string | null;
    avatarUrl: string | null;
    isActive: boolean;
    isSuperuser: boolean;
    isVerified: boolean;
}