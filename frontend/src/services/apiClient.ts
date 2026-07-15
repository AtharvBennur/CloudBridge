import axios from "axios";

import { env } from "@/lib/env";

export const apiClient = axios.create({
  baseURL: env.apiBaseUrl,
  timeout: 10_000,
  headers: {
    "Content-Type": "application/json",
  },
});

apiClient.interceptors.request.use((config) => {
  const stored = (() => {
    try { return sessionStorage.getItem("cloudbridge_auth"); } catch { return null; }
  })();
  if (stored) {
    try {
      const data = JSON.parse(stored);
      if (data.token) {
        config.headers.Authorization = `Bearer ${data.token}`;
      }
    } catch {}
  }
  return config;
});

apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    const message = error.response?.data?.error?.message || "Unable to complete the request.";
    return Promise.reject(new Error(message));
  },
);
