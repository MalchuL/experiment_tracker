export interface ApiTokenCreateRequest {
  name: string;
  description?: string;
  scopes: string[];
  expiresInDays?: number;
}

export interface ApiTokenCreateResponse {
  id: string;
  name: string;
  token: string;
  createdAt: string;
}

export interface ApiTokenListItem {
  id: string;
  name: string;
  description?: string | null;
  scopes: string[];
  createdAt: string;
  expiresAt?: string | null;
  revoked: boolean;
  lastUsedAt?: string | null;
}

export interface ApiTokenUpdateRequest {
  name?: string;
  description?: string;
  scopes?: string[];
  expiresInDays?: number;
}
