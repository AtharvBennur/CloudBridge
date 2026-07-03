export interface LoginRequest {
  email: string;
  password: string;
}

export interface AuthUser {
  email: string;
  displayName: string;
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

    const user: AuthUser = {
      email: request.email.trim().toLowerCase(),
      displayName: request.email.split("@")[0],
    };

    window.sessionStorage.setItem(SESSION_STORAGE_KEY, JSON.stringify(user));
    return user;
  },

  async logout(): Promise<void> {
    window.sessionStorage.removeItem(SESSION_STORAGE_KEY);
  },

  getCurrentUser(): AuthUser | null {
    const rawSession = window.sessionStorage.getItem(SESSION_STORAGE_KEY);
    if (!rawSession) {
      return null;
    }

    try {
      return JSON.parse(rawSession) as AuthUser;
    } catch {
      window.sessionStorage.removeItem(SESSION_STORAGE_KEY);
      return null;
    }
  },
};
