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
    const user: AuthUser = response.data.user || {
      email: request.email.trim().toLowerCase(),
      displayName: request.email.split("@")[0],
    };

    // Use a resilient storage accessor: prefer sessionStorage but fall back to localStorage
    const storage = ((): Storage => {
      try {
        const s = window.sessionStorage;
        const testKey = "__cloudbridge_test";
        s.setItem(testKey, "1");
        s.removeItem(testKey);
        return s;
      } catch {
        return window.localStorage;
      }
    })();

    storage.setItem(SESSION_STORAGE_KEY, JSON.stringify({ user, message: response.data.message }));
    return user;
  },

  async googleOAuthLogin(request: GoogleOAuthRequest): Promise<AuthUser> {
    const response = await apiClient.post<AuthApiMessage>("/auth/google-oauth", request);
    const user: AuthUser = response.data.user || {
      email: request.email || "user@gmail.com",
      displayName: request.name || "Google User",
    };

    const storage = ((): Storage => {
      try {
        const s = window.sessionStorage;
        const testKey = "__cloudbridge_test";
        s.setItem(testKey, "1");
        s.removeItem(testKey);
        return s;
      } catch {
        return window.localStorage;
      }
    })();

    storage.setItem(SESSION_STORAGE_KEY, JSON.stringify({ user, message: response.data.message }));
    return user;
  },

  async logout(): Promise<void> {
    await apiClient.post<AuthApiMessage>("/auth/logout");
    const storage = ((): Storage => {
      try {
        const s = window.sessionStorage;
        const testKey = "__cloudbridge_test";
        s.setItem(testKey, "1");
        s.removeItem(testKey);
        return s;
      } catch {
        return window.localStorage;
      }
    })();

    storage.removeItem(SESSION_STORAGE_KEY);
  },

  async getCurrentUser(): Promise<AuthUser | null> {
    try {
      const response = await apiClient.get<AuthApiMessage>("/auth/me");
      const storage = ((): Storage => {
        try {
          const s = window.sessionStorage;
          const testKey = "__cloudbridge_test";
          s.setItem(testKey, "1");
          s.removeItem(testKey);
          return s;
        } catch {
          return window.localStorage;
        }
      })();

      const rawSession = storage.getItem(SESSION_STORAGE_KEY);
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
