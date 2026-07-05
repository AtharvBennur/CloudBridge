import { apiClient } from "@/services/apiClient";

export interface LoginRequest {
  email: string;
  password: string;
}

export interface AuthUser {
  email: string;
  displayName: string;
}

export interface AuthApiMessage {
  message: string;
}

const SESSION_STORAGE_KEY = "cloudbridge.session";

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
    const user: AuthUser = {
      email: request.email.trim().toLowerCase(),
      displayName: request.email.split("@")[0],
    };

    window.sessionStorage.setItem(SESSION_STORAGE_KEY, JSON.stringify({ user, message: response.data.message }));
    return user;
  },

  async logout(): Promise<void> {
    await apiClient.post<AuthApiMessage>("/auth/logout");
    window.sessionStorage.removeItem(SESSION_STORAGE_KEY);
  },

  async getCurrentUser(): Promise<AuthUser | null> {
    try {
      const response = await apiClient.get<AuthApiMessage>("/auth/me");
      const rawSession = window.sessionStorage.getItem(SESSION_STORAGE_KEY);
      if (!rawSession) {
        return null;
      }

      const session = JSON.parse(rawSession) as { user?: AuthUser; message?: string };
      if (session.user) {
        return session.user;
      }

      return response.data.message ? { email: "pending@example.com", displayName: "Pending" } : null;
    } catch {
      window.sessionStorage.removeItem(SESSION_STORAGE_KEY);
      return null;
    }
  },
};
