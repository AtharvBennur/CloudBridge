import { apiClient } from "@/services/apiClient";

export interface LoginRequest {
  email: string;
  password: string;
}

export interface GoogleOAuthRequest {
  id_token: string;
  email?: string;
  name?: string;
}

export interface AuthUser {
  email: string;
  displayName: string;
}

export interface AuthApiMessage {
  message: string;
  user?: AuthUser;
  token?: string;
}

const STORAGE_KEY = "cloudbridge_auth";

function getStoredAuth(): { user?: { email: string; displayName: string }; token?: string } | null {
  try {
    const d = sessionStorage.getItem(STORAGE_KEY);
    return d ? JSON.parse(d) : null;
  } catch {
    return null;
  }
}

function setStoredAuth(data: { user: { email: string; displayName: string }; token?: string }): void {
  try {
    sessionStorage.setItem(STORAGE_KEY, JSON.stringify(data));
  } catch {
    try { localStorage.setItem(STORAGE_KEY, JSON.stringify(data)); } catch {}
  }
}

function clearStoredAuth(): void {
  try {
    sessionStorage.removeItem(STORAGE_KEY);
  } catch {
    try { localStorage.removeItem(STORAGE_KEY); } catch {}
  }
}

function assertValidLoginRequest(request: LoginRequest): void {
  if (!request.email.includes("@")) {
    throw new Error("Use a valid email address.");
  }

  if (request.password.length < 8) {
    throw new Error("Password must be at least 8 characters.");
  }
}

export const authService = {
  async login(request: LoginRequest): Promise<AuthUser> {
    assertValidLoginRequest(request);

    const response = await apiClient.post<AuthApiMessage>("/auth/login", request);
    const user: AuthUser = response.data.user || {
      email: request.email.trim().toLowerCase(),
      displayName: request.email.split("@")[0],
    };

    setStoredAuth({ user, token: response.data.token });
    return user;
  },

  async googleOAuthLogin(request: GoogleOAuthRequest): Promise<AuthUser> {
    const response = await apiClient.post<AuthApiMessage>("/auth/google-oauth", request);
    const user: AuthUser = response.data.user || {
      email: request.email || "user@gmail.com",
      displayName: request.name || "Google User",
    };

    setStoredAuth({ user, token: response.data.token });
    return user;
  },

  async logout(): Promise<void> {
    try {
      await apiClient.post<AuthApiMessage>("/auth/logout");
    } catch {
      // Proceed with local logout even if the server call fails
    }
    clearStoredAuth();
  },

  async getCurrentUser(): Promise<AuthUser | null> {
    const stored = getStoredAuth();
    if (!stored?.token) {
      return null;
    }

    try {
      const response = await apiClient.get<AuthApiMessage>("/auth/me");
      if (response.data.user) {
        setStoredAuth({ user: response.data.user, token: response.data.token || stored.token });
        return response.data.user;
      }
      // Fallback: if API returns no user but we have a stored user, try that
      if (stored.user) {
        return stored.user as AuthUser;
      }
      return null;
    } catch {
      clearStoredAuth();
      return null;
    }
  },
};
